# src/bog_builder.py
import xml.etree.ElementTree as ET
from xml.dom import minidom
import zipfile

class BogFolderBuilder:
    """Builds a Niagara .bog file containing a folder with multiple components and links."""

    def __init__(self, folder_name):
        # The root element must be 'bajaObjectGraph'
        self.root = ET.Element('bajaObjectGraph')
        self.root.set('version', '4.0')
        self.root.set('reversibleEncodingKeySource', 'none')
        self.root.set('FIPSEnabled', 'false')
        self.root.set('reversibleEncodingValidator', '[null.1]=')

        # All components go inside an UnrestrictedFolder
        unrestricted_folder = ET.SubElement(self.root, 'p', {'t': 'b:UnrestrictedFolder', 'm': 'b=baja'})
        self.folder = ET.SubElement(unrestricted_folder, 'p', {'n': folder_name, 't': 'b:Folder'})
        
        # --- State for Auto-Layout ---
        self._next_handle = 1
        self._link_counters = {} 
        self._current_x = 50
        self._current_y = 50
        self.x_offset = 140  # Horizontal distance between blocks
        self.y_offset = 70   # Vertical distance for new rows

    def _get_next_handle(self):
        """Generates a unique hex handle string for components (e.g., '1', 'a', '1f')."""
        handle = hex(self._next_handle)[2:]
        self._next_handle += 1
        return handle

    def add_component(self, comp_type, name, properties=None, ws_annotation=None):
        """
        Adds a component to the folder. If ws_annotation is None, it will be
        placed automatically using the "typewriter" layout.
        """
        handle_str = self._get_next_handle()
        comp_attrs = {'n': name, 't': comp_type, 'h': handle_str}
        
        if ':' in comp_type:
            prefix = comp_type.split(':')[0]
            comp_attrs['m'] = f"{prefix}={prefix}"

        component_element = ET.SubElement(self.folder, 'p', comp_attrs)
        
        if properties:
            for prop_name, prop_value in properties.items():
                ET.SubElement(component_element, 'p', {'n': prop_name, 'v': str(prop_value)})

        # --- Auto-Layout Logic ---
        if ws_annotation is None:
            # Use automatic "typewriter" placement
            annotation_str = f"{self._current_x},{self._current_y},8"
            ET.SubElement(component_element, 'p', {'n': 'wsAnnotation', 't': 'b:WsAnnotation', 'v': annotation_str})
            # Move the "cursor" for the next block
            self._current_x += self.x_offset
        else:
            # Use the manually provided placement
            ET.SubElement(component_element, 'p', {'n': 'wsAnnotation', 't': 'b:WsAnnotation', 'v': ws_annotation})
            
        return component_element
    
    def new_row(self):
        """Resets the x-coordinate and moves the y-coordinate down for the next component."""
        self._current_x = 50
        self._current_y += self.y_offset

    def add_link(self, source_comp_handle, source_slot, target_comp_handle, target_slot):
        """Adds a link between two components."""
        target_element = self.folder.find(f'.//p[@h="{target_comp_handle}"]')
        if target_element is None:
            raise ValueError(f"Could not find target component with handle {target_comp_handle}")

        link_count = self._link_counters.get(target_comp_handle, 0)
        link_name = "Link" if link_count == 0 else f"Link{link_count}"
        self._link_counters[target_comp_handle] = link_count + 1

        link_attrs = {'n': link_name, 't': 'b:Link', 'm': 'b=baja'}
        link_element = ET.SubElement(target_element, 'p', link_attrs)
        
        source_ord_value = f"h:{source_comp_handle}"
        ET.SubElement(link_element, 'p', {'n': 'sourceOrd', 'v': source_ord_value})
        ET.SubElement(link_element, 'p', {'n': 'sourceSlotName', 'v': source_slot})
        ET.SubElement(link_element, 'p', {'n': 'targetSlotName', 'v': target_slot})
        ET.SubElement(link_element, 'p', {'n': 'relationId', 'v': 'n:dataLink'})
        ET.SubElement(link_element, 'p', {'n': 'relationTags', 'v': ''})

    def save(self, file_path):
        """Saves the constructed component to a .bog file."""
        rough_string = ET.tostring(self.root, 'utf-8')
        reparsed = minidom.parseString(rough_string)
        pretty_string = reparsed.toprettyxml(indent="  ", encoding="utf-8")

        with zipfile.ZipFile(file_path, 'w') as bog_zip:
            bog_zip.writestr('file.xml', pretty_string)
        print(f"Successfully wrote bog file to {file_path}")