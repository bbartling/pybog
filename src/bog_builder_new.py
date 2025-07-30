# src/bog_builder.py
import xml.etree.ElementTree as ET
from xml.dom import minidom
import zipfile
from collections import defaultdict, deque
import os

class BogFolderBuilder:
    """
    Builds a Niagara .bog file with an intelligent layout engine.
    Supports automatic recursive sub-folder creation to manage complexity.
    """

    def __init__(self, folder_name, debug=True):
        """Initializes the builder with a root folder name."""
        self.debug = debug
        self.folder_name = folder_name
        self._components = {}
        self._links = []
        self._next_handle = 1
        self._handle_map = {}
        self._sub_folders = defaultdict(list)
        self._component_to_folder = {}
        self._current_folder_path = (folder_name,)

        # --- NEW: Threshold for automatic sub-folder creation ---
        # If a folder's logic is wider than this, it will be split.
        self.MAX_TIERS_PER_FOLDER = 5

        # Layout constants - NOT TO BE MODIFIED
        self.START_X = 10
        self.START_Y = 10
        self.X_COLUMN_WIDTH = 15
        self.Y_INCREMENT = 10

    def log(self, message):
        if self.debug:
            print(f"[BOG DEBUG] {message}")

    def _get_next_handle(self):
        handle = hex(self._next_handle)[2:]
        self._next_handle += 1
        return handle

    def start_sub_folder(self, name):
        """Starts a new sub-folder context."""
        parent_path = self._current_folder_path
        self._sub_folders[parent_path].append(name)
        self._current_folder_path = parent_path + (name,)
        self.log(f"Entered sub-folder: {self.get_current_path_str()}")
        return self._current_folder_path

    def end_sub_folder(self):
        """Exits the current sub-folder, returning to the parent."""
        if len(self._current_folder_path) > 1:
            self._current_folder_path = self._current_folder_path[:-1]
            self.log(f"Returned to folder: {self.get_current_path_str()}")
        else:
            self.log("Already at the root folder.")

    def get_current_path_str(self):
        return "/".join(self._current_folder_path)

    def add_component(self, comp_type, name, properties=None, actions=None):
        """Registers a component in the current folder context."""
        if name in self._components:
            raise ValueError(f"Component with name '{name}' already exists.")
        handle = self._get_next_handle()
        self._handle_map[name] = handle
        self._components[name] = {"type": comp_type, "properties": properties or {}, "actions": actions or {}, "handle": handle}
        self._component_to_folder[name] = self._current_folder_path
        self.log(f"Added component '{name}' to folder '{self.get_current_path_str()}'")

    def add_link(self, source_comp_name, source_slot, target_comp_name, target_slot):
        """Adds a link, creating proxies if it crosses a folder boundary."""
        if source_comp_name not in self._components:
            raise ValueError(f"Source component '{source_comp_name}' not found.")
        if target_comp_name not in self._components:
            raise ValueError(f"Target component '{target_comp_name}' not found.")

        self._add_direct_link(source_comp_name, source_slot, target_comp_name, target_slot)

    def _add_direct_link(self, source_comp_name, source_slot, target_comp_name, target_slot):
        """Internal method to add a link to the global registry."""
        source_type = self._components[source_comp_name]["type"]
        link_type = "b:Link"
        if "Boolean" in source_type and target_slot.startswith("in"):
            source_comp_info = self._components.get(source_comp_name, {})
            if source_comp_info.get("type") == "control:BooleanWritable":
                link_type = "b:ConversionLink"
        self._links.append({"source_name": source_comp_name, "source_slot": source_slot, "target_name": target_comp_name, "target_slot": target_slot, "link_type": link_type})
        self.log(f"Registered link: '{source_comp_name}.{source_slot}' -> '{target_comp_name}.{target_slot}'")

    def save(self, file_path):
        """Constructs the XML and saves it to a .bog file."""
        final_xml_root = self._build_xml_recursive()
        rough_string = ET.tostring(final_xml_root, "utf-8")
        reparsed = minidom.parseString(rough_string)
        pretty_string = reparsed.toprettyxml(indent="  ", encoding="utf-8")
        with zipfile.ZipFile(file_path, "w") as bog_zip:
            bog_zip.writestr("file.xml", pretty_string)
        self.log(f"Successfully wrote .bog file to {file_path}")

    def _build_xml_recursive(self):
        """Builds the entire XML structure, starting from the root."""
        root = ET.Element("bajaObjectGraph", {"version": "4.0", "reversibleEncodingKeySource": "none", "FIPSEnabled": "false", "reversibleEncodingValidator": "[null.1]"})
        unrestricted_folder = ET.SubElement(root, "p", {"t": "b:UnrestrictedFolder", "m": "b=baja"})
        self._build_folder_contents(unrestricted_folder, (self.folder_name,))
        return root

    def _build_folder_contents(self, parent_xml_element, folder_path_tuple):
        """Builds the XML for a single folder, automatically splitting it if it's too wide."""
        folder_name = folder_path_tuple[-1]
        folder_element = ET.SubElement(parent_xml_element, "p", {"n": folder_name, "t": "b:Folder"})
        
        components_in_folder = {name: data for name, data in self._components.items() if self._component_to_folder.get(name) == folder_path_tuple}
        if not components_in_folder:
            for sub_folder_name in self._sub_folders.get(folder_path_tuple, []):
                self._build_folder_contents(folder_element, folder_path_tuple + (sub_folder_name,))
            return

        # --- Layout Calculation and Automatic Splitting ---
        levels = self._calculate_levels(components_in_folder)
        
        if len(levels) > self.MAX_TIERS_PER_FOLDER:
            self.log(f"Folder '{folder_name}' is too wide ({len(levels)} tiers). Splitting...")
            self._split_folder_logic(folder_path_tuple, levels)
            # After splitting, we need to re-calculate the components for the current folder
            components_in_folder = {name: data for name, data in self._components.items() if self._component_to_folder.get(name) == folder_path_tuple}
            levels = self._calculate_levels(components_in_folder)

        # --- Positioning and XML Generation for the (potentially smaller) folder ---
        comp_coords = self._position_components(levels)
        self._add_component_xml_tags(folder_element, components_in_folder, comp_coords)
        
        # Create proxies and add link tags
        self._create_proxies_and_add_link_tags(folder_element, components_in_folder)

        # --- Recursive call for sub-folders ---
        for sub_folder_name in self._sub_folders.get(folder_path_tuple, []):
            self._build_folder_contents(folder_element, folder_path_tuple + (sub_folder_name,))

    def _calculate_levels(self, components_in_scope):
        """Performs a topological sort to determine the layout tiers."""
        in_degree = {name: 0 for name in components_in_scope}
        adj = defaultdict(list)
        for link in self._links:
            source, target = link["source_name"], link["target_name"]
            if source in components_in_scope and target in components_in_scope:
                adj[source].append(target)
                in_degree[target] += 1
        
        queue = deque([name for name in components_in_scope if in_degree[name] == 0])
        levels = []
        visited = set()
        while queue:
            level_size = len(queue)
            current_level = []
            for _ in range(level_size):
                u = queue.popleft()
                if u in visited: continue
                visited.add(u)
                current_level.append(u)
                for v in sorted(adj[u]):
                    in_degree[v] -= 1
                    if in_degree[v] == 0:
                        queue.append(v)
            if current_level:
                levels.append(current_level)
        return levels

    def _split_folder_logic(self, folder_path_tuple, levels):
        """Moves logic beyond the tier threshold into a new sub-folder."""
        split_tier = self.MAX_TIERS_PER_FOLDER
        components_to_move = set()
        for i in range(split_tier, len(levels)):
            for comp_name in levels[i]:
                components_to_move.add(comp_name)

        continuation_folder_name = f"{folder_path_tuple[-1]}_Continuation_1"
        new_folder_path = folder_path_tuple + (continuation_folder_name,)
        
        # Register the new sub-folder
        self._sub_folders[folder_path_tuple].append(continuation_folder_name)

        # Re-assign components to the new folder
        for comp_name in components_to_move:
            self._component_to_folder[comp_name] = new_folder_path
            self.log(f"Moving component '{comp_name}' to new folder '{'/'.join(new_folder_path)}'")

    def _position_components(self, levels):
        """Calculates X,Y coordinates for a set of components based on their levels."""
        comp_coords = {}
        current_x = self.START_X
        for level in levels:
            # Simple vertical layout for now
            y_pos = self.START_Y
            for name in level:
                comp_coords[name] = (current_x, y_pos)
                y_pos += self.Y_INCREMENT
            current_x += self.X_COLUMN_WIDTH
        return comp_coords

    def _create_proxies_and_add_link_tags(self, folder_element, components_in_folder):
        """Creates proxy points for cross-folder links and adds all link tags."""
        links_in_folder = [l for l in self._links if l['target_name'] in components_in_folder]
        
        for link in links_in_folder:
            source_folder = self._component_to_folder.get(link["source_name"])
            target_folder = self._component_to_folder.get(link["target_name"])

            if source_folder != target_folder:
                # This is a cross-boundary link, create an input proxy
                proxy_name = f"ProxyIn_{link['target_name']}_{link['target_slot']}"
                if proxy_name not in self._components:
                    # Temporarily switch context to add the proxy component
                    original_folder_ctx = self._current_folder_path
                    self._current_folder_path = target_folder
                    self.add_numeric_writable(proxy_name)
                    self._current_folder_path = original_folder_ctx
                
                # The original link is now split into two
                self._add_link_tag_to_xml(folder_element, link["source_name"], link["source_slot"], proxy_name, "in16", link["link_type"])
                self._add_link_tag_to_xml(folder_element, proxy_name, "out", link["target_name"], link["target_slot"], "b:Link")
            else:
                # This is a direct link within the same folder
                self._add_link_tag_to_xml(folder_element, link["source_name"], link["source_slot"], link["target_name"], link["target_slot"], link["link_type"])

    def _add_component_xml_tags(self, folder_element, components, coords):
        """Adds the <p> tags for components to the XML tree."""
        for name, data in components.items():
            attrs = {"n": name, "t": data["type"], "h": data["handle"]}
            if ":" in data["type"]:
                prefix = data["type"].split(":")[0]
                attrs["m"] = f"{prefix}={prefix}"
            element = ET.SubElement(folder_element, "p", attrs)
            
            x, y = coords.get(name, (self.START_X, self.START_Y))
            ET.SubElement(element, "p", {"n": "wsAnnotation", "t": "b:WsAnnotation", "v": f"{int(x)},{int(y)},8"})

            if data["type"] == "control:NumericWritable":
                default_val = data["properties"].get("defaultValue", 0.0)
                out_slot = ET.SubElement(element, "p", {"n": "out", "f": "s", "t": "b:StatusNumeric"})
                ET.SubElement(out_slot, "p", {"n": "value", "v": str(default_val)})
                ET.SubElement(out_slot, "p", {"n": "status", "v": "0;activeLevel=e:17@control:PriorityLevel"})
                fallback_slot = ET.SubElement(element, "p", {"n": "fallback", "t": "b:StatusNumeric"})
                ET.SubElement(fallback_slot, "p", {"n": "value", "v": str(default_val)})
                ET.SubElement(element, "p", {"n": "in16", "f": "tsL"})
            elif data["type"] == "control:BooleanWritable":
                fallback_slot = ET.SubElement(element, "p", {"n": "fallback", "t": "b:StatusBoolean"})
                ET.SubElement(fallback_slot, "p", {"n": "value", "v": data["properties"]["fallback"]["value"]})
            else:
                for prop_name, prop_value in data["properties"].items():
                    ET.SubElement(element, "p", {"n": prop_name, "v": str(prop_value)})
            for action_name, action_flag in data["actions"].items():
                ET.SubElement(element, "a", {"n": action_name, "f": action_flag})

    def _add_link_tag_to_xml(self, folder_element, source_name, source_slot, target_name, target_slot, link_type):
        """Finds the target component in the XML and appends a single link tag."""
        target_handle = self._handle_map.get(target_name)
        if not target_handle: return
        target_element = folder_element.find(f".//p[@h='{target_handle}']")
        if target_element is None: return

        # Need a unique link name per target
        link_count = len(target_element.findall('p[@t="b:Link"]')) + len(target_element.findall('p[@t="b:ConversionLink"]'))
        link_name = f"Link{link_count + 1}" if link_count > 0 else "Link"

        link_element = ET.SubElement(target_element, "p", {"n": link_name, "t": link_type})
        ET.SubElement(link_element, "p", {"n": "sourceSlotName", "v": source_slot})
        ET.SubElement(link_element, "p", {"n": "sourceOrd", "v": f"h:{self._handle_map[source_name]}"})
        ET.SubElement(link_element, "p", {"n": "targetSlotName", "v": target_slot})
        if link_type == "b:ConversionLink":
            ET.SubElement(link_element, "p", {"n": "converter", "m": "conv=converters", "t": "conv:StatusBooleanToStatusNumeric"})

    # Helper methods
    def add_numeric_writable(self, name, default_value=0.0):
        self.add_component("control:NumericWritable", name, properties={"defaultValue": default_value}, actions={"emergencyOverride": "h", "emergencyAuto": "h"})
    def add_numeric_switch(self, name):
        self.add_component("kitControl:NumericSwitch", name)
    def add_boolean_writable(self, name, default_value=False):
        self.add_component("control:BooleanWritable", name, properties={"fallback": {"value": str(default_value).lower()}}, actions={"emergencyActive": "h", "emergencyInactive": "h", "emergencyAuto": "h"})
    def add_reduction_block(self, block_type, final_output_name, input_names):
        assert block_type in ("Average", "Minimum", "Maximum"), "Unsupported block type"
        MAX_INPUTS = 4
        tier = 1
        current_inputs = input_names[:]
        self.start_sub_folder(f"{block_type}Calc")
        while len(current_inputs) > MAX_INPUTS:
            tier_outputs = []
            for i in range(0, len(current_inputs), MAX_INPUTS):
                chunk = current_inputs[i : i + MAX_INPUTS]
                node_name = f"{block_type}_T{tier}_{i//MAX_INPUTS}"
                self.add_component(f"kitControl:{block_type}", node_name)
                for j, input_name in enumerate(chunk):
                    self.add_link(input_name, "out", node_name, f"in{chr(65 + j)}")
                tier_outputs.append(node_name)
            current_inputs = tier_outputs
            tier += 1
        final_block = f"{block_type}_T{tier}_final"
        self.add_component(f"kitControl:{block_type}", final_block)
        for j, input_name in enumerate(current_inputs):
            self.add_link(input_name, "out", final_block, f"in{chr(65 + j)}")
        self.end_sub_folder()
        self.add_numeric_writable(name=final_output_name)
        self.add_link(final_block, "out", final_output_name, "in16")
