# src/bog_builder.py
import xml.etree.ElementTree as ET
from xml.dom import minidom

class BogBuilder:
    """Builds a Niagara .bog file programmatically."""

    def __init__(self, component_type, component_name):
        """
        Initializes the builder with a root component.
        Args:
            component_type (str): The Niagara type (e.g., 'control:Program').
            component_name (str): The desired name for the component.
        """
        # Create the root <bog> element
        self.root = ET.Element('bog')
        # Create the main component element
        self.component = ET.SubElement(self.root, component_type, {'n': component_name})

    def add_slot(self, name, value, slot_type=None):
        """
        Adds a slot (<p> tag) to the main component.
        Args:
            name (str): The name of the slot.
            value (str): The value of the slot.
            slot_type (str, optional): The Niagara type of the slot. Defaults to None.
        """
        attrs = {'n': name, 'v': str(value)}
        if slot_type:
            attrs['t'] = slot_type
        
        ET.SubElement(self.component, 'p', attrs)
        return self # Allow chaining calls

    def save(self, file_path):
        """
        Saves the constructed component to a .bog file with proper formatting.
        Args:
            file_path (str): The path to save the new .bog file.
        """
        # Convert the ElementTree object to a string
        rough_string = ET.tostring(self.root, 'utf-8')
        
        # Use minidom to prettify the XML for readability
        reparsed = minidom.parseString(rough_string)
        pretty_string = reparsed.toprettyxml(indent="  ", encoding="utf-8")

        with open(file_path, 'wb') as f:
            f.write(pretty_string)
        print(f"Successfully wrote bog file to {file_path}")
