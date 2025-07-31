# src/bog_builder.py
import xml.etree.ElementTree as ET
from xml.dom import minidom
import zipfile
from collections import defaultdict, deque


class BogFolderBuilder:
    """
    Builds a Niagara .bog file with a non-negotiable, intelligent layout engine
    that strictly adheres to the Hierarchical Data Flow strategy.
    """

    def __init__(self, folder_name, debug=True):
        """Initializes the builder with a root folder name."""
        self.debug = debug
        self.folder_name = folder_name
        self._components = {}
        self._links = []
        self._next_handle = 1
        self._handle_map = {}

        # Layout constants
        self.START_X = 10
        self.START_Y = 10
        self.X_COLUMN_WIDTH = 15  # Increased for better spacing between columns
        self.Y_INCREMENT = 10  # Increased for better vertical spacing

    def log(self, message):
        """Prints a debug message if debugging is enabled."""
        if self.debug:
            print(f"[BOG DEBUG] {message}")

    def _get_next_handle(self):
        """Generates a unique hex handle string."""
        handle = hex(self._next_handle)[2:]
        self._next_handle += 1
        return handle

    def add_component(self, comp_type, name, properties=None, actions=None):
        """Registers a component. Layout is 100% automatic."""
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
        self.log(f"Added component '{name}' ({comp_type})")

    def add_link(self, source_comp_name, source_slot, target_comp_name, target_slot):
        """Adds a link between two components, with automatic type conversion."""
        if source_comp_name not in self._components:
            raise ValueError(f"Source component '{source_comp_name}' not found.")
        if target_comp_name not in self._components:
            raise ValueError(f"Target component '{target_comp_name}' not found.")

        source_type = self._components[source_comp_name]["type"]

        # Determine if a conversion link is needed
        link_type = "b:Link"
        if "Boolean" in source_type and target_slot.startswith("in"):
            # A more robust check for boolean-like types
            source_comp_info = self._components.get(source_comp_name, {})
            if source_comp_info.get("type") == "control:BooleanWritable":
                link_type = "b:ConversionLink"

        self._links.append(
            {
                "source_name": source_comp_name,
                "source_slot": source_slot,
                "target_name": target_comp_name,
                "target_slot": target_slot,
                "link_type": link_type,
            }
        )
        self.log(
            f"Linked [{link_type}] '{source_comp_name}.{source_slot}' -> '{target_comp_name}.{target_slot}'"
        )

    def add_numeric_writable(self, name, default_value=0.0):
        """Helper to add a standard control:NumericWritable component."""
        self.add_component(
            "control:NumericWritable",
            name,
            properties={"defaultValue": default_value},
            actions={"emergencyOverride": "h", "emergencyAuto": "h"},
        )

    def add_numeric_switch(self, name):
        """Adds a kitControl:NumericSwitch component (not util)."""
        self.add_component("kitControl:NumericSwitch", name)

    def add_boolean_writable(self, name, default_value=False):
        """Helper to add a standard control:BooleanWritable component."""
        self.add_component(
            "control:BooleanWritable",
            name,
            properties={"fallback": {"value": str(default_value).lower()}},
            actions={
                "emergencyActive": "h",
                "emergencyInactive": "h",
                "emergencyAuto": "h",
            },
        )

    def save(self, file_path):
        """Constructs the XML and saves it to a .bog file."""
        final_xml_root = self._build_xml()
        # Use minidom for pretty printing the XML
        rough_string = ET.tostring(final_xml_root, "utf-8")
        reparsed = minidom.parseString(rough_string)
        pretty_string = reparsed.toprettyxml(indent="  ", encoding="utf-8")

        with zipfile.ZipFile(file_path, "w") as bog_zip:
            bog_zip.writestr("file.xml", pretty_string)
        self.log(f"Successfully wrote .bog file to {file_path}")

    def add_reduction_block(self, block_type, final_output_name, input_names):
        assert block_type in ("Average", "Minimum", "Maximum"), "Unsupported block type"
        MAX_INPUTS = 4
        tier = 1
        current_inputs = input_names[:]

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

        self.add_numeric_writable(name=final_output_name)
        self.add_link(final_block, "out", final_output_name, "in16")

    def _build_xml(self):
        """Lays out components and constructs the final XML tree before saving."""
        self.log("Starting XML build process...")

        root = ET.Element(
            "bajaObjectGraph",
            {
                "version": "4.0",
                "reversibleEncodingKeySource": "none",
                "FIPSEnabled": "false",
                "reversibleEncodingValidator": "[null.1]",
            },
        )
        unrestricted_folder = ET.SubElement(
            root, "p", {"t": "b:UnrestrictedFolder", "m": "b=baja"}
        )
        folder_element = ET.SubElement(
            unrestricted_folder, "p", {"n": self.folder_name, "t": "b:Folder"}
        )

        # Perform a topological sort to arrange components in tiers/levels
        in_degree = {name: 0 for name in self._components}
        adj = defaultdict(list)
        for link in self._links:
            adj[link["source_name"]].append(link["target_name"])
            in_degree[link["target_name"]] += 1

        # Initialize queue with nodes that have no incoming links
        queue = deque(
            [name for name in sorted(self._components) if in_degree[name] == 0]
        )
        levels = []
        visited = set()

        while queue:
            level_size = len(queue)
            current_level = []
            for _ in range(level_size):
                u = queue.popleft()
                if u in visited:
                    continue
                visited.add(u)
                current_level.append(u)
                for v in sorted(adj[u]):
                    in_degree[v] -= 1
                    if in_degree[v] == 0:
                        queue.append(v)
            if current_level:
                levels.append(current_level)

        comp_coords = {}
        current_x = self.START_X

        # Layout the first tier (source components)
        if levels:
            level_zero_y = self.START_Y
            for name in levels[0]:
                comp_coords[name] = (current_x, level_zero_y)
                level_zero_y += self.Y_INCREMENT

        current_x += self.X_COLUMN_WIDTH

        # Layout subsequent tiers with fan-out handling
        for level in levels[1:]:
            def avg_input_y(name):
                """Average Y of all connected parent nodes."""
                ys = [
                    comp_coords[link["source_name"]][1]
                    for link in self._links
                    if link["target_name"] == name
                    and link["source_name"] in comp_coords
                ]
                return sum(ys) / len(ys) if ys else self.START_Y

            # Calculate desired positions
            desired_positions = [
                {"name": name, "y": avg_input_y(name)} for name in level
            ]
            desired_positions.sort(key=lambda p: p["y"])

            # Pass 1: Collision resolution (push down)
            last_y = -float("inf")
            for pos in desired_positions:
                y_pos = max(pos["y"], last_y + self.Y_INCREMENT)
                comp_coords[pos["name"]] = (current_x, y_pos)
                last_y = y_pos

            # Pass 2: Centering tier vertically
            all_y = [
                coord[1] for coord in comp_coords.values() if coord[0] == current_x
            ]
            avg_y = sum(all_y) / len(all_y)
            tier_shift = self.START_Y + ((len(levels[0]) * self.Y_INCREMENT) / 2) - avg_y
            for name in [p["name"] for p in desired_positions]:
                x, y = comp_coords[name]
                comp_coords[name] = (x, y + tier_shift)

            current_x += self.X_COLUMN_WIDTH


        # === OUTPUT SIDE-CAR LOGIC ===
        # Position output-only writables next to their driver component
        for name, data in self._components.items():
            if data["type"] in ("control:NumericWritable", "control:BooleanWritable"):
                is_output_only = all(
                    link["source_name"] != name for link in self._links
                )
                if is_output_only:
                    incoming_links = [
                        l for l in self._links if l["target_name"] == name
                    ]
                    if incoming_links:
                        # Place it next to its first input driver
                        driver = incoming_links[0]["source_name"]
                        if driver in comp_coords:
                            sx, sy = comp_coords[driver]
                            comp_coords[name] = (sx + self.X_COLUMN_WIDTH, sy)

        # === FINAL XML ELEMENT CONSTRUCTION ===
        link_counters = defaultdict(int)
        for name, data in self._components.items():
            attrs = {"n": name, "t": data["type"], "h": data["handle"]}
            if ":" in data["type"]:
                prefix = data["type"].split(":")[0]
                attrs["m"] = f"{prefix}={prefix}"
            element = ET.SubElement(folder_element, "p", attrs)

            x, y = comp_coords.get(name, (self.START_X, self.START_Y))
            ET.SubElement(
                element,
                "p",
                {
                    "n": "wsAnnotation",
                    "t": "b:WsAnnotation",
                    "v": f"{int(x)},{int(y)},8",
                },
            )

            # Add component-specific properties and slots
            if data["type"] == "control:NumericWritable":
                default_val = data["properties"].get("defaultValue", 0.0)
                out_slot = ET.SubElement(
                    element, "p", {"n": "out", "f": "s", "t": "b:StatusNumeric"}
                )
                ET.SubElement(out_slot, "p", {"n": "value", "v": str(default_val)})
                ET.SubElement(
                    out_slot,
                    "p",
                    {"n": "status", "v": "0;activeLevel=e:17@control:PriorityLevel"},
                )
                fallback_slot = ET.SubElement(
                    element, "p", {"n": "fallback", "t": "b:StatusNumeric"}
                )
                ET.SubElement(fallback_slot, "p", {"n": "value", "v": str(default_val)})
                ET.SubElement(element, "p", {"n": "in16", "f": "tsL"})
            elif data["type"] == "control:BooleanWritable":
                fallback_slot = ET.SubElement(
                    element, "p", {"n": "fallback", "t": "b:StatusBoolean"}
                )
                ET.SubElement(
                    fallback_slot,
                    "p",
                    {"n": "value", "v": data["properties"]["fallback"]["value"]},
                )
            else:
                for prop_name, prop_value in data["properties"].items():
                    ET.SubElement(element, "p", {"n": prop_name, "v": str(prop_value)})

            for action_name, action_flag in data["actions"].items():
                ET.SubElement(element, "a", {"n": action_name, "f": action_flag})

        # Wire all the links between components
        for link in self._links:
            target_handle = self._handle_map[link["target_name"]]
            target_element = folder_element.find(f".//p[@h='{target_handle}']")

            # Ensure target element was found before proceeding
            if target_element is None:
                self.log(
                    f"WARNING: Could not find target element for link to '{link['target_name']}'"
                )
                continue

            link_count = link_counters[link["target_name"]]
            link_name = f"Link{link_count + 1}" if link_count > 0 else "Link"
            link_counters[link["target_name"]] += 1

            link_element = ET.SubElement(
                target_element, "p", {"n": link_name, "t": link["link_type"]}
            )
            ET.SubElement(
                link_element, "p", {"n": "sourceSlotName", "v": link["source_slot"]}
            )
            ET.SubElement(
                link_element,
                "p",
                {"n": "sourceOrd", "v": f"h:{self._handle_map[link['source_name']]}"},
            )
            ET.SubElement(
                link_element, "p", {"n": "targetSlotName", "v": link["target_slot"]}
            )

            if link["link_type"] == "b:ConversionLink":
                ET.SubElement(
                    link_element,
                    "p",
                    {
                        "n": "converter",
                        "m": "conv=converters",
                        "t": "conv:StatusBooleanToStatusNumeric",
                    },
                )

        return root
