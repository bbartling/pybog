# src/bog_parser.py
import xml.etree.ElementTree as ET

class BogParser:
    """Parses a Niagara .bog file to analyze its component structure."""

    def __init__(self, file_path):
        """
        Initializes the parser by loading and parsing the XML file.
        Args:
            file_path (str): The path to the .bog file.
        """
        try:
            self.tree = ET.parse(file_path)
            self.root = self.tree.getroot()
            # The main component is usually the first child of the root
            self.component = self.root[0]
        except ET.ParseError as e:
            raise ValueError(f"Error parsing XML file: {e}")
        except IndexError:
            raise ValueError("BOG file appears to be empty or invalid.")

    def get_component_type(self):
        """Returns the type of the main component (e.g., 'control:NumericWritable')."""
        return self.component.tag

    def get_component_name(self):
        """Returns the name of the main component."""
        return self.component.get('n', 'Unnamed')

    def list_slots(self):
        """
        Returns a list of dictionaries, each representing a slot (property).
        A slot is a <p> tag inside the main component.
        """
        slots = []
        # Slots are direct children <p> tags of the component
        for prop in self.component.findall('p'):
            slot_info = {
                'name': prop.get('n'),
                'value': prop.get('v'),
                'type': prop.get('t')
            }
            slots.append(slot_info)
        return slots

    def find_slot_value(self, slot_name):
        """
        Finds the value of a specific slot by its name.
        Args:
            slot_name (str): The name of the slot to find (e.g., 'facets').
        Returns:
            The value of the slot, or None if not found.
        """
        for prop in self.component.findall('p'):
            if prop.get('n') == slot_name:
                return prop.get('v')
        return None