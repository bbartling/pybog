# src/bog_builder.py
import xml.etree.ElementTree as ET
from xml.dom import minidom
import zipfile
from collections import defaultdict, deque
import os

class BogFolderBuilder:
    """
    Builds a Niagara .bog file with an intelligent layout engine.
    Now supports automatic sub-folder creation to manage complexity.
    """

    def __init__(self, folder_name, debug=True):
        """Initializes the builder with a root folder name."""
        self.debug = debug
        self.folder_name = folder_name
        self._components = {}  # Global component registry
        self._links = []       # Global link registry
        self._next_handle = 1
        self._handle_map = {}
        self._sub_folders = defaultdict(list) # parent_path -> [child_folder_names]
        self._component_to_folder = {} # component_name -> folder_path as tuple

        # The current folder context for adding new components
        self._current_folder_path = (folder_name,)

        # Layout constants - NOT TO BE MODIFIED
        self.START_X = 10
        self.START_Y = 10
        self.X_COLUMN_WIDTH = 20 # Increased for better visual separation
        self.Y_INCREMENT = 15    # Increased for better visual separation

    def log(self, message, is_layout_log=False):
        """Prints a debug message if debugging is enabled."""
        if self.debug and is_layout_log:
            print(f"[BOG LAYOUT DEBUG] {message}")

    def _get_next_handle(self):
        handle = hex(self._next_handle)[2:]
        self._next_handle += 1
        return handle

    def start_sub_folder(self, name):
        """Starts a new sub-folder context."""
        parent_path = self._current_folder_path
        self._sub_folders[parent_path].append(name)
        self._current_folder_path = parent_path + (name,)

    def end_sub_folder(self):
        """Exits the current sub-folder, returning to the parent."""
        if len(self._current_folder_path) > 1:
            self._current_folder_path = self._current_folder_path[:-1]

    def get_current_path_str(self):
        """Returns the current folder path as a string."""
        return "/".join(self._current_folder_path)

    def add_component(self, comp_type, name, properties=None, actions=None):
        """Registers a component in the current folder context."""
        if name in self._components:
            raise ValueError(f"Component with name '{name}' already exists.")
        handle = self._get_next_handle()
        self._handle_map[name] = handle
        self._components[name] = {
            "type": comp_type,
            "properties": properties or {},
            "actions": actions or {},
            "handle": handle,
        }
        self._component_to_folder[name] = self._current_folder_path

    def add_link(self, source_comp_name, source_slot, target_comp_name, target_slot):
        """Adds a link, creating directional proxies if it crosses a folder boundary."""
        if source_comp_name not in self._components:
            raise ValueError(f"Source component '{source_comp_name}' not found.")
        if target_comp_name not in self._components:
            raise ValueError(f"Target component '{target_comp_name}' not found.")

        self._add_direct_link(source_comp_name, source_slot, target_comp_name, target_slot)


    def save(self, file_path):
        """Constructs the XML and saves it to a .bog file."""
        final_xml_root = self._build_xml_recursive()
        rough_string = ET.tostring(final_xml_root, "utf-8")
        reparsed = minidom.parseString(rough_string)
        pretty_string = reparsed.toprettyxml(indent="  ", encoding="utf-8")
        with zipfile.ZipFile(file_path, "w") as bog_zip:
            bog_zip.writestr("file.xml", pretty_string)

    def _build_xml_recursive(self):
        """Builds the entire XML structure, starting from the root."""
        root = ET.Element("bajaObjectGraph", {"version": "4.0", "reversibleEncodingKeySource": "none", "FIPSEnabled": "false", "reversibleEncodingValidator": "[null.1]"})
        unrestricted_folder = ET.SubElement(root, "p", {"t": "b:UnrestrictedFolder", "m": "b=baja"})
        self._build_folder_contents(unrestricted_folder, (self.folder_name,))
        return root


    def _build_folder_contents(self, parent_xml_element, folder_path_tuple):
        """Builds the XML for a single folder, flattening only sub-folder icons at the top level."""
        folder_name = folder_path_tuple[-1]
        self.log(f"--- Building folder: {'/'.join(folder_path_tuple)} ---", is_layout_log=True)

        # Create XML <p> element for this folder
        folder_element = ET.SubElement(parent_xml_element, "p", {"n": folder_name, "t": "b:Folder"})

        # Get all components assigned to this folder
        components_in_folder = {
            name: data
            for name, data in self._components.items()
            if self._component_to_folder.get(name) == folder_path_tuple
        }
        #self.log(f"Components in folder {folder_name}: {list(components_in_folder.keys())}", is_layout_log=True)

        if len(folder_path_tuple) == 1:
            # TOP LEVEL: position inputs, outputs, and subfolder icons
            sub_folders_in_this_view = self._sub_folders.get(folder_path_tuple, [])
            comp_coords = self._position_top_level_interface(components_in_folder, sub_folders_in_this_view)

            # Flatten Y only for sub-folder icons at top level
            for sf in sub_folders_in_this_view:
                if sf in comp_coords:
                    old_x, old_y = comp_coords[sf]
                    comp_coords[sf] = (old_x, self.START_Y)
                    #self.log(f"Flattened sub-folder '{sf}' from ({old_x}, {old_y}) to ({old_x}, {self.START_Y})", is_layout_log=True)

        else:
            # LOGIC SUBFOLDER: normal tiered layout
            levels = self._calculate_levels(components_in_folder)
            comp_coords = self._position_components_normally(levels)
            #self.log(f"Calculated levels for {folder_name}: {levels}", is_layout_log=True)

        # Add components with wsAnnotation tags
        self._add_component_xml_tags(folder_element, components_in_folder, comp_coords)

        # Add links targeting this folder
        links_targeting_this_folder = [
            l for l in self._links if self._component_to_folder.get(l['target_name']) == folder_path_tuple
        ]
        #self.log(f"Links targeting {folder_name}: {links_targeting_this_folder}", is_layout_log=True)
        self._add_link_xml_tags(folder_element, links_targeting_this_folder)

        # Recurse into subfolders
        for sub_folder_name in self._sub_folders.get(folder_path_tuple, []):
            self.log(f"About to recurse into sub-folder: {sub_folder_name}", is_layout_log=True)
            self._build_folder_contents(folder_element, folder_path_tuple + (sub_folder_name,))


    def _position_top_level_interface(self, components, sub_folders):
        """Special layout for the root folder: Inputs (left) | Folders (center) | Outputs (right)."""
        self.log("Using TOP-LEVEL interface layout.", is_layout_log=True)
        coords = {}
        inputs, outputs = [], []
        
        all_links_sources = {l['source_name'] for l in self._links}
        all_links_targets = {l['target_name'] for l in self._links}

        # Categorize components
        for name, data in components.items():
            if data['type'].endswith('Writable') and name in all_links_targets and name not in all_links_sources:
                outputs.append(name)
            elif data['type'].endswith('Writable'):
                inputs.append(name)

        self.log(f"Categorized as INPUTS: {sorted(inputs)}", is_layout_log=True)
        self.log(f"Categorized as OUTPUTS: {sorted(outputs)}", is_layout_log=True)
        self.log(f"Found SUB-FOLDERS: {sorted(sub_folders)}", is_layout_log=True)

        # Place INPUTS (left column)
        y = self.START_Y
        for name in sorted(inputs):
            coords[name] = (self.START_X, y)
            self.log(f"Positioned INPUT '{name}' at ({coords[name][0]}, {coords[name][1]})", is_layout_log=True)
            y += self.Y_INCREMENT

        # Place SUB-FOLDERS (middle column, FLAT at START_Y)
        folder_x = self.START_X + self.X_COLUMN_WIDTH * 3
        for folder_name in sorted(sub_folders):
            coords[folder_name] = (folder_x, self.START_Y)
            self.log(f"Positioned FOLDER '{folder_name}' flat at ({coords[folder_name][0]}, {coords[folder_name][1]})", is_layout_log=True)

        # Place OUTPUTS (right column)
        y = self.START_Y
        output_x = self.START_X + self.X_COLUMN_WIDTH * 3
        for name in sorted(outputs):
            coords[name] = (output_x, y)
            self.log(f"Positioned OUTPUT '{name}' at ({coords[name][0]}, {coords[name][1]})", is_layout_log=True)
            y += self.Y_INCREMENT

        return coords


    def _position_components_normally(self, levels):
        """Calculates X,Y coordinates for components inside a logic folder."""
        self.log(f"Using NORMAL component layout across {len(levels)} tiers.", is_layout_log=True)
        comp_coords = {}
        current_x = self.START_X
        for i, level in enumerate(levels):
            y_pos = self.START_Y
            self.log(f"  Positioning Tier {i+1} with {len(level)} components.", is_layout_log=True)
            for name in level:
                comp_coords[name] = (current_x, y_pos)
                y_pos += self.Y_INCREMENT
            current_x += self.X_COLUMN_WIDTH
        return comp_coords

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
        levels, visited = [], set()
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


    def _add_direct_link(self, source_name, source_slot, target_name, target_slot):
        s_type = self._components[source_name]["type"]
        t_type = self._components[target_name]["type"]

        link_type = "b:Link"
        converter_type = None

        # Helpers
        def target_is_boolean_like(t, slot):
            # Boolean blocks / slots that expect boolean input
            if t in (
                "kitControl:And", "kitControl:Or", "kitControl:Xor",
                "kitControl:BooleanDelay", "kitControl:OneShot",
            ):
                return True
            # NumericSwitch inSwitch is boolean
            if t == "kitControl:NumericSwitch" and slot == "inSwitch":
                return True
            return False

        def target_is_numeric_like(t, slot):
            # Numeric math / clamp blocks or numeric inputs
            if t.startswith("kitControl:") and t.split(":")[1] in (
                "Add","Subtract","Multiply","Divide",
                "Average","Minimum","Maximum",
            ):
                return True
            # Generic heuristic: many kitControl numeric blocks use StatusNumeric on 'in*'
            return "Numeric" in t

        # 1) Enum case: NumericSelect.select expects enum (from numeric)
        if t_type == "kitControl:NumericSelect" and target_slot == "select":
            link_type = "b:ConversionLink"
            converter_type = "conv:StatusNumericToStatusEnum"

        # 2) Boolean → Numeric ONLY when target is numeric-like (and not inSwitch)
        elif "Boolean" in s_type and target_slot.startswith("in") \
            and not target_is_boolean_like(t_type, target_slot) \
            and target_is_numeric_like(t_type, target_slot):
            link_type = "b:ConversionLink"
            converter_type = "conv:StatusBooleanToStatusNumeric"

        # 3) Numeric (StatusNumeric) -> Counter.countIncrement needs Number
        elif t_type == "kitControl:Counter" and target_slot == "countIncrement":
            # Niagara expects a numeric->number converter here
            link_type = "b:ConversionLink"
            converter_type = "conv:StatusNumericToNumber"


        self._links.append({
            "source_name": source_name,
            "source_slot": source_slot,
            "target_name": target_name,
            "target_slot": target_slot,
            "link_type": link_type,
            "converter_type": converter_type
        })


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

                # NEW: emit facets if provided
                facets_prop = data["properties"].get("facets")
                if isinstance(facets_prop, dict) and facets_prop.get("type") == "b:Facets":
                    ET.SubElement(
                        element, "p",
                        {"n": "facets", "t": "b:Facets", "v": str(facets_prop.get("value", ""))}
                    )
                elif isinstance(facets_prop, str):
                    ET.SubElement(element, "p", {"n": "facets", "t": "b:Facets", "v": facets_prop})

                ET.SubElement(element, "p", {"n": "in16", "f": "tsL"})

            elif data["type"] == "control:BooleanWritable":
                fallback_prop = data["properties"].get("fallback", {})
                fallback_val = fallback_prop.get("value", "false")
                fallback_slot = ET.SubElement(element, "p", {"n": "fallback", "t": "b:StatusBoolean"})
                ET.SubElement(fallback_slot, "p", {"n": "value", "v": str(fallback_val).lower()})

            elif data["type"] == "kitControl:NumericConst":
                const_val = data["properties"].get("out", 0.0)
                out_slot = ET.SubElement(element, "p", {"n": "out", "t": "b:StatusNumeric"})
                ET.SubElement(out_slot, "p", {"n": "value", "v": str(const_val)})
            
            # This revised logic now correctly generates the full XML for a NumericSwitch
            elif data["type"] == "kitControl:NumericSwitch":
                # Define the 'inSwitch' slot with its full structure
                in_switch_slot = ET.SubElement(element, "p", {"n": "inSwitch", "f": "sL", "t": "b:StatusBoolean"})
                ET.SubElement(in_switch_slot, "p", {"n": "value", "v": "false"})
                ET.SubElement(in_switch_slot, "p", {"n": "status", "v": "0;activeLevel=e:17@control:PriorityLevel"})

                # Define the 'inTrue' slot with its full structure
                in_true_slot = ET.SubElement(element, "p", {"n": "inTrue", "f": "sL", "t": "b:StatusNumeric"})
                ET.SubElement(in_true_slot, "p", {"n": "value", "v": "0.0"})
                
                # Define the 'inFalse' slot with its full structure
                in_false_slot = ET.SubElement(element, "p", {"n": "inFalse", "f": "sL", "t": "b:StatusNumeric"})
                ET.SubElement(in_false_slot, "p", {"n": "value", "v": "0.0"})

                # Also handle any other simple properties passed in
                for prop_name, prop_value in data["properties"].items():
                    ET.SubElement(element, "p", {"n": prop_name, "v": str(prop_value)})

            elif data["type"] == "kitControl:BooleanDelay":
                # Input slot stub (so a link target exists even before wiring)
                ET.SubElement(element, "p", {"n": "in", "f": "sL"})

                # onDelay / offDelay must be RelTime
                on_d = data["properties"].get("onDelay", "0")
                off_d = data["properties"].get("offDelay", "0")
                if isinstance(on_d, dict):
                    on_d = on_d.get("value", "0")
                if isinstance(off_d, dict):
                    off_d = off_d.get("value", "0")

                ET.SubElement(element, "p", {"n": "onDelay",  "t": "b:RelTime", "v": str(on_d)})
                ET.SubElement(element, "p", {"n": "offDelay", "t": "b:RelTime", "v": str(off_d)})

            elif data["type"] == "control:TimeTrigger":
                # Emit triggerMode as a scalar value (required by Niagara)
                tm = data["properties"].get("triggerMode")
                if isinstance(tm, dict) and "value" in tm:
                    ET.SubElement(
                        element, "p",
                        {"n": "triggerMode", "t": "control:IntervalTriggerMode", "v": str(tm["value"])}
                    )
                elif isinstance(tm, str):
                    ET.SubElement(
                        element, "p",
                        {"n": "triggerMode", "t": "control:IntervalTriggerMode", "v": tm}
                    )
                # emit any other simple properties for TimeTrigger
                for prop_name, prop_value in data["properties"].items():
                    if prop_name == "triggerMode":
                        continue  # already handled
                    ET.SubElement(element, "p", {"n": prop_name, "v": str(prop_value)})

            elif data["type"] == "kitControl:MultiVibrator":
                # Emit scalar RelTime for 'period' like: <p n="period" t="b:RelTime" v="10000"/>
                per = data["properties"].get("period", "10000")
                if isinstance(per, dict):
                    per = per.get("value", "10000")
                ET.SubElement(element, "p", {"n": "period", "t": "b:RelTime", "v": str(per)})

            elif data["type"] == "kitControl:OneShot":
                ET.SubElement(element, "p", {"n": "in", "f": "sL"})

            elif data["type"] == "kitControl:Counter":
                props = data.get("properties", {})

                # --- OUT: StatusNumeric with optional value + precision ---
                # Always create the out slot as a StatusNumeric "s" (structured) value.
                out_slot = ET.SubElement(element, "p", {"n": "out", "f": "s", "t": "b:StatusNumeric"})

                init_out = props.get("outValue")
                if init_out is not None:
                    # Optionally round to precision for nicer initial render
                    prec = props.get("precision")
                    if prec is not None:
                        try:
                            init_out = round(float(init_out), int(prec))
                        except Exception:
                            pass
                    ET.SubElement(out_slot, "p", {"n": "value", "v": str(init_out)})

                precision = props.get("precision")
                if precision is not None:
                    ET.SubElement(out_slot, "p", {"n": "precision", "v": str(int(precision))})

                # --- INPUTS: typed boolean link targets for control ---
                # Count up / down direction inputs should be StatusBoolean link targets
                ET.SubElement(element, "p", {"n": "countUp", "f": "sL", "t": "b:StatusBoolean"})
                # Provide countDown too (harmless if unused; useful for ping-pong patterns)
                ET.SubElement(element, "p", {"n": "countDown", "f": "sL", "t": "b:StatusBoolean"})

                # --- CONFIG: numeric parameters as Floats ---
                inc = props.get("countIncrement")
                if inc is not None:
                    ET.SubElement(element, "p", {"n": "countIncrement", "f": "L", "t": "b:Float", "v": str(inc)})

                init_val = props.get("initialValue")
                if init_val is not None:
                    ET.SubElement(element, "p", {"n": "initialValue", "f": "L", "t": "b:Float", "v": str(init_val)})

                # --- ACTION: clear (action link target) ---
                ET.SubElement(element, "a", {"n": "clear", "f": "aL"})


            else:
                # This is the generic logic for all other component types
                for prop_name, prop_value in data["properties"].items():
                    if isinstance(prop_value, dict) and 'type' in prop_value and 'value' in prop_value:
                        prop_element = ET.SubElement(element, "p", {"n": prop_name, "t": prop_value['type']})
                        ET.SubElement(prop_element, "p", {"n": "value", "v": str(prop_value['value'])})
                    else:
                        ET.SubElement(element, "p", {"n": prop_name, "v": str(prop_value)})

            for action_name, action_flag in data["actions"].items():
                ET.SubElement(element, "a", {"n": action_name, "f": action_flag})


    def _add_link_xml_tags(self, folder_element, links):
        """(Revised) Adds the <p> tags for links to the XML tree."""
        link_counters = defaultdict(int)
        for link in links:
            target_handle = self._handle_map.get(link["target_name"])
            if not target_handle: continue
            target_element = folder_element.find(f"./p[@h='{target_handle}']")
            if target_element is None: continue

            link_count = link_counters[link["target_name"]]
            link_name = f"Link{link_count + 1}" if link_count > 0 else "Link"
            link_counters[link["target_name"]] += 1

            link_element = ET.SubElement(target_element, "p", {"n": link_name, "t": link["link_type"]})
            ET.SubElement(link_element, "p", {"n": "sourceSlotName", "v": link["source_slot"]})
            ET.SubElement(link_element, "p", {"n": "sourceOrd", "v": f"h:{self._handle_map[link['source_name']]}"})
            ET.SubElement(link_element, "p", {"n": "targetSlotName", "v": link["target_slot"]})

            # REVISED LOGIC IS HERE
            # This is no longer hardcoded. It checks if a converter is needed
            # and uses the specific type that was stored with the link.
            if link.get("converter_type"):
                ET.SubElement(link_element, "p", {"n": "converter", "m": "conv=converters", "t": link["converter_type"]})

    # Helper methods from original file
    def add_numeric_writable(self, name, default_value=0.0, precision=2, units="u:null"):
        facets_value = f"units={units};;;;|precision=i:{precision}|min=d:-inf|max=d:+inf"
        self.add_component(
            "control:NumericWritable",
            name,
            properties={
                "defaultValue": default_value,
                "facets": {"type": "b:Facets", "value": facets_value},
            },
            actions={"emergencyOverride": "h", "emergencyAuto": "h"},
        )

    def add_numeric_switch(self, name):
        self.add_component("kitControl:NumericSwitch", name)

    def add_numeric_select(self, name):
        """Adds a NumericSelect component with default 10 inputs (A-J)."""
        self.add_component("kitControl:NumericSelect", name, properties={"numberValues": "10"})

    def add_boolean_writable(self, name, default_value=False):
        self.add_component("control:BooleanWritable", name, properties={"fallback": {"value": str(default_value).lower()}}, actions={"emergencyActive": "h", "emergencyInactive": "h", "emergencyAuto": "h"})

    def add_multi_vibrator(self, name, period_ms="10000"):
        # period_ms may be string or int; we emit b:RelTime scalar
        self.add_component("kitControl:MultiVibrator", name, properties={"period": str(period_ms)})

    def add_counter(self, name, count_increment=1.0, initial_value=0.0, precision=None, properties=None):
        props = dict(properties or {})
        props.setdefault("countIncrement", count_increment)
        props.setdefault("initialValue", initial_value)
        if precision is not None:
            props["precision"] = int(precision)
        self.add_component("kitControl:Counter", name, properties=props)
        
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
