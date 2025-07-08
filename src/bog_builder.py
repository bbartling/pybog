# src/bog_builder.py
import xml.etree.ElementTree as ET
from xml.dom import minidom
import zipfile

class BogFolderBuilder:
    """
    Builds a Niagara .bog file, incorporating production-quality features
    for component slots, actions, and layout based on a defined strategy.
    """

    def __init__(self, folder_name):
        self.root = ET.Element('bajaObjectGraph', {
            'version': '4.0',
            'reversibleEncodingKeySource': 'none',
            'FIPSEnabled': 'false',
            'reversibleEncodingValidator': '[null.1]='
        })
        unrestricted_folder = ET.SubElement(self.root, 'p', {'t': 'b:UnrestrictedFolder', 'm': 'b=baja'})
        self.folder = ET.SubElement(unrestricted_folder, 'p', {'n': folder_name, 't': 'b:Folder'})
        
        # --- State for Auto-Layout ---
        self._next_handle = 1
        self._link_counters = {} 
        self._current_x = 50
        self._current_y = 50
        self._row_max_y = 50
        self.x_offset = 180
        self.y_offset = 100
        self.wrap_at_x = 700

    def _get_next_handle(self):
        handle = hex(self._next_handle)[2:]
        self._next_handle += 1
        return handle

    def new_row(self):
        """Resets x and increments y to start a new visual row."""
        self._current_x = 50
        self._current_y = self._row_max_y + self.y_offset
        self._row_max_y = self._current_y

    def add_component(self, comp_type, name, properties=None, settable=False, readonly=False, default_value=None):
        """
        Adds a component with enhanced options for slot configuration and layout.
        """
        handle_str = self._get_next_handle()
        comp_attrs = {'n': name, 't': comp_type, 'h': handle_str}
        
        if ':' in comp_type:
            prefix = comp_type.split(':')[0]
            comp_attrs['m'] = f"{prefix}={prefix}"

        # --- Auto-Layout ---
        if self._current_x > self.wrap_at_x:
            self.new_row()
        annotation_str = f"{self._current_x},{self._current_y},8"
        self._current_x += self.x_offset
        self._row_max_y = max(self._row_max_y, self._current_y)
        
        component_element = ET.SubElement(self.folder, 'p', comp_attrs)
        ET.SubElement(component_element, 'p', {'n': 'wsAnnotation', 't': 'b:WsAnnotation', 'v': annotation_str})

        # --- Enhanced Slot/Action Configuration ---
        if settable:
            ET.SubElement(component_element, 'a', {'n': 'override', 'f': 'ho'})
            ET.SubElement(component_element, 'a', {'n': 'auto', 'f': 'ho'})
            ET.SubElement(component_element, 'a', {'n': 'emergencyOverride', 'f': 'h'})
            ET.SubElement(component_element, 'a', {'n': 'emergencyAuto', 'f': 'h'})

            if default_value is not None:
                # Complex property for default value
                out_slot = ET.SubElement(component_element, 'p', {'n': 'out', 'f': 's', 't': 'b:StatusNumeric'})
                ET.SubElement(out_slot, 'p', {'n': 'value', 'v': str(default_value)})
                ET.SubElement(out_slot, 'p', {'n': 'status', 'v': '0;activeLevel=e:17@control:PriorityLevel'})
                fallback_slot = ET.SubElement(component_element, 'p', {'n': 'fallback', 't': 'b:StatusNumeric'})
                ET.SubElement(fallback_slot, 'p', {'n': 'value', 'v': str(default_value)})
            else:
                ET.SubElement(component_element, 'p', {'n': 'out', 'f': 's'})

        if readonly:
            ET.SubElement(component_element, 'p', {'n': 'out', 'f': 'h'})
            ET.SubElement(component_element, 'a', {'n': 'set', 'f': 'ho'})
            ET.SubElement(component_element, 'a', {'n': 'override', 'f': 'ho'})
            ET.SubElement(component_element, 'a', {'n': 'auto', 'f': 'ho'})
            ET.SubElement(component_element, 'a', {'n': 'emergencyOverride', 'f': 'h'})
            ET.SubElement(component_element, 'a', {'n': 'emergencyAuto', 'f': 'h'})

        if properties:
            for prop_name, prop_value in properties.items():
                ET.SubElement(component_element, 'p', {'n': prop_name, 'v': str(prop_value)})
            
        return component_element

    def add_link(self, source_comp_handle, source_slot, target_comp_handle, target_slot):
        """Adds a verbose, production-style link between two components."""
        target_element = self.folder.find(f'.//p[@h="{target_comp_handle}"]')
        if target_element is None:
            raise ValueError(f"Could not find target component with handle {target_comp_handle}")

        link_count = self._link_counters.get(target_comp_handle, 0)
        link_name = "Link" if link_count == 0 else f"Link{link_count}"
        self._link_counters[target_comp_handle] = link_count + 1

        link_element = ET.SubElement(target_element, 'p', {'n': link_name, 't': 'b:Link'})
        ET.SubElement(link_element, 'p', {'n': 'sourceOrd', 'v': f"h:{source_comp_handle}"})
        ET.SubElement(link_element, 'p', {'n': 'sourceSlotName', 'v': source_slot})
        ET.SubElement(link_element, 'p', {'n': 'targetSlotName', 'v': target_slot})
        ET.SubElement(link_element, 'p', {'n': 'relationId', 'v': 'n:dataLink'})

    def save(self, file_path):
        """Saves the constructed XML to a .bog file."""
        rough_string = ET.tostring(self.root, 'utf-8')
        reparsed = minidom.parseString(rough_string)
        pretty_string = reparsed.toprettyxml(indent="  ", encoding="utf-8")

        with zipfile.ZipFile(file_path, 'w') as bog_zip:
            bog_zip.writestr('file.xml', pretty_string)
        print(f"Successfully wrote bog file to {file_path}")
