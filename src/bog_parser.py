# src/bog_parser.py
import xml.etree.ElementTree as ET
import zipfile
import io

class BogParser:
    """Parses a Niagara .bog file by reading the file.xml from its ZIP archive."""

    def __init__(self, file_path, debug=False):
        """
        Initializes the parser by opening the .bog file as a ZIP archive
        and parsing the 'file.xml' within.
        Args:
            file_path (str): The path to the .bog file.
            debug (bool): If True, prints extra debugging information.
        """
        self.debug = debug
        try:
            with zipfile.ZipFile(file_path, 'r') as bog_zip:
                xml_bytes = bog_zip.read('file.xml')
                
                if self.debug:
                    print("--- Raw XML Bytes (first 200) ---")
                    print(xml_bytes[:200])
                    print("---------------------------------")

                try:
                    xml_content = xml_bytes.decode('utf-8-sig')
                except UnicodeDecodeError:
                    if self.debug:
                        print("UTF-8-SIG decoding failed. Falling back to latin-1.")
                    xml_content = xml_bytes.decode('latin-1')
                
                self.root = ET.fromstring(xml_content)

        except zipfile.BadZipFile:
            raise ValueError(f"File is not a valid .bog (ZIP) file: {file_path}")
        except KeyError:
            raise ValueError("The .bog file does not contain a 'file.xml' entry.")
        except ET.ParseError as e:
            raise ValueError(f"Error parsing XML content from .bog file: {e}")
        except FileNotFoundError:
            raise FileNotFoundError(f"The file was not found at path: {file_path}")

    def find_component(self, path):
        """
        Finds a component element at a specific path.
        Example path: './p[1]/p[@n="ClgControlLogic"]'
        """
        return self.root.find(path)

    def list_slots(self, component_element):
        """
        Returns a list of dictionaries for slots of a given component element.
        """
        if component_element is None:
            return []
        slots = []
        for prop in component_element.findall('p'):
            slot_info = {
                'name': prop.get('n'),
                'value': prop.get('v'),
                'type': prop.get('t')
            }
            slots.append(slot_info)
        return slots

    def print_tree(self, element=None, indent=""):
        """
        Recursively prints the XML tree structure for debugging purposes.
        """
        if element is None:
            element = self.root
        attrs = ' '.join([f'{k}="{v}"' for k, v in element.attrib.items()])
        print(f"{indent}<{element.tag} {attrs}>")
        for child in element:
            self.print_tree(child, indent + "  ")