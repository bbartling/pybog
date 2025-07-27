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

    def __init__(self, folder_name):
        """Initializes the builder with a root folder name."""
        self.folder_name = folder_name
        self._components = {}
        self._links = []
        self._next_handle = 1
        self._handle_map = {}

        self.START_X = 10
        self.START_Y = 10
        self.X_COLUMN_WIDTH = 15
        self.Y_INCREMENT = 10
        self.Y_INCREMENT_TIGHT = 10
        self.MAX_X = 592

    def average(self, final_output_name, input_names):
        self.add_reduction_block("Average", final_output_name, input_names)

    def minimum(self, final_output_name, input_names):
        self.add_reduction_block("Minimum", final_output_name, input_names)

    def maximum(self, final_output_name, input_names):
        self.add_reduction_block("Maximum", final_output_name, input_names)


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
            'type': comp_type,
            'properties': properties or {},
            'actions': actions or {},
            'handle': handle
        }

    def add_reduction_block(self, block_type, final_output_name, input_names):
        """
        Adds a reduction block (Average, Minimum, Maximum) that supports N inputs.
        Niagara blocks support only 4 inputs, so this method builds a reduction tree
        and wires it automatically.
        
        Parameters:
            block_type (str): One of "Average", "Minimum", "Maximum"
            final_output_name (str): Name of the final output numericWritable
            input_names (list[str]): List of input component names
        """
        from math import ceil

        assert block_type in ("Average", "Minimum", "Maximum"), "Unsupported block type"
        MAX_INPUTS = 4
        tier = 1
        current_inputs = input_names[:]

        # Step 1: Build tree of reduction blocks until final node
        while len(current_inputs) > MAX_INPUTS:
            tier_outputs = []
            for i in range(0, len(current_inputs), MAX_INPUTS):
                chunk = current_inputs[i:i+MAX_INPUTS]
                node_name = f"{block_type}_T{tier}_{i//MAX_INPUTS}"
                self.add_component(f"kitControl:{block_type}", node_name)
                for j, input_name in enumerate(chunk):
                    self.add_link(input_name, "out", node_name, f"in{chr(65 + j)}")
                tier_outputs.append(node_name)
            current_inputs = tier_outputs
            tier += 1

        # Step 2: Final block
        final_block = f"{block_type}_T{tier}_final"
        self.add_component(f"kitControl:{block_type}", final_block)
        for j, input_name in enumerate(current_inputs):
            self.add_link(input_name, "out", final_block, f"in{chr(65 + j)}")

        # Step 3: Final writable output
        self.add_numeric_writable(name=final_output_name)
        self.add_link(final_block, "out", final_output_name, "in16")


    def add_numeric_writable(self, name, default_value=0.0):
        """
        Helper to register a standard control:NumericWritable component.
        """
        standard_actions = {
            'emergencyOverride': 'h',
            'emergencyAuto': 'h'
        }
        self.add_component(
            'control:NumericWritable', name,
            properties={'defaultValue': default_value},
            actions=standard_actions
        )

    def add_link(self, source_comp_name, source_slot, target_comp_name, target_slot):
        """Registers a link between two components."""
        if source_comp_name not in self._components:
            raise ValueError(f"Source component '{source_comp_name}' not found.")
        if target_comp_name not in self._components:
            raise ValueError(f"Target component '{target_comp_name}' not found.")
        self._links.append({
            'source_name': source_comp_name, 'source_slot': source_slot,
            'target_name': target_comp_name, 'target_slot': target_slot
        })

    def _build_xml(self):
        """Lays out components and constructs the final XML tree before saving."""
        root = ET.Element('bajaObjectGraph', {
            'version': '4.0',
            'reversibleEncodingKeySource': 'none',
            'FIPSEnabled': 'false',
            'reversibleEncodingValidator': '[null.1]'
        })
        unrestricted_folder = ET.SubElement(root, 'p', {'t': 'b:UnrestrictedFolder', 'm': 'b=baja'})
        folder_element = ET.SubElement(unrestricted_folder, 'p', {'n': self.folder_name, 't': 'b:Folder'})

        # Build graph structure
        in_degree = {name: 0 for name in self._components}
        adj = defaultdict(list)
        for link in self._links:
            adj[link['source_name']].append(link['target_name'])
            in_degree[link['target_name']] += 1

        queue = deque([name for name in sorted(self._components) if in_degree[name] == 0])
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
            levels.append(current_level)

        comp_coords = {}
        current_x = self.START_X

        # Initial vertical pass
        current_y = self.START_Y
        if levels:
            for name in levels[0]:
                comp_coords[name] = (current_x, current_y)
                current_y += self.Y_INCREMENT

        current_x += self.X_COLUMN_WIDTH

        # Remaining tiers
        for level in levels[1:]:
            def avg_input_y(name):
                ys = [
                    comp_coords[link['source_name']][1]
                    for link in self._links
                    if link['target_name'] == name and link['source_name'] in comp_coords
                ]
                return sum(ys) / len(ys) if ys else self.START_Y

            sorted_level = sorted(level, key=avg_input_y)

            # Compute total vertical space needed for this tier
            total_height = len(sorted_level) * self.Y_INCREMENT
            start_y = self.START_Y + (len(levels[0]) * self.Y_INCREMENT // 2) - (total_height // 2)

            for i, name in enumerate(sorted_level):
                y_pos = start_y + i * self.Y_INCREMENT
                comp_coords[name] = (current_x, y_pos)

            current_x += self.X_COLUMN_WIDTH

        # XML build
        link_counters = defaultdict(int)
        for name, data in self._components.items():
            attrs = {'n': name, 't': data['type'], 'h': data['handle']}
            if ':' in data['type']:
                prefix = data['type'].split(':')[0]
                attrs['m'] = f"{prefix}={prefix}"
            element = ET.SubElement(folder_element, 'p', attrs)

            x, y = comp_coords.get(name, (self.START_X, self.START_Y))
            ET.SubElement(element, 'p', {'n': 'wsAnnotation', 't': 'b:WsAnnotation', 'v': f"{int(x)},{int(y)},8"})

            if data['type'] == 'control:NumericWritable':
                default_val = data['properties'].get('defaultValue', 0.0)
                out_slot = ET.SubElement(element, 'p', {'n': 'out', 'f': 's', 't': 'b:StatusNumeric'})
                ET.SubElement(out_slot, 'p', {'n': 'value', 'v': str(default_val)})
                ET.SubElement(out_slot, 'p', {'n': 'status', 'v': '0;activeLevel=e:17@control:PriorityLevel'})
                fallback_slot = ET.SubElement(element, 'p', {'n': 'fallback', 't': 'b:StatusNumeric'})
                ET.SubElement(fallback_slot, 'p', {'n': 'value', 'v': str(default_val)})
                ET.SubElement(element, 'p', {'n': 'in16', 'f': 'tsL'})
            else:
                for prop_name, prop_value in data['properties'].items():
                    ET.SubElement(element, 'p', {'n': prop_name, 'v': str(prop_value)})

            for action_name, action_flag in data['actions'].items():
                ET.SubElement(element, 'a', {'n': action_name, 'f': action_flag})

        # Wire links
        for link in self._links:
            target_handle = self._handle_map[link['target_name']]
            target_element = folder_element.find(f".//p[@h='{target_handle}']")
            link_count = link_counters[link['target_name']]
            link_name = "Link" if link_count == 0 else f"Link{link_count}"
            link_counters[link['target_name']] += 1

            link_element = ET.SubElement(target_element, 'p', {'n': link_name, 't': 'b:Link'})
            ET.SubElement(link_element, 'p', {'n': 'relationTags', 'v': ''})
            ET.SubElement(link_element, 'p', {'n': 'sourceSlotName', 'v': link['source_slot']})
            ET.SubElement(link_element, 'p', {'n': 'sourceOrd', 'v': f"h:{self._handle_map[link['source_name']]}"})
            ET.SubElement(link_element, 'p', {'n': 'relationId', 'v': 'n:dataLink'})
            ET.SubElement(link_element, 'p', {'n': 'targetSlotName', 'v': link['target_slot']})

        return root


    def save(self, file_path):
        """Saves the constructed component to a .bog file."""
        final_xml_root = self._build_xml()
        rough_string = ET.tostring(final_xml_root, 'utf-8')
        reparsed = minidom.parseString(rough_string)
        pretty_string = reparsed.toprettyxml(indent="  ", encoding="utf-8")

        with zipfile.ZipFile(file_path, 'w') as bog_zip:
            bog_zip.writestr('file.xml', pretty_string)
        print(f"Successfully wrote .bog file to {file_path}")
