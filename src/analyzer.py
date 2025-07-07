# src/analyzer.py
import xml.etree.ElementTree as ET
import zipfile
import io
import os
import re
import json

class Analyzer:
    """
    A universal analyzer for Niagara .bog and .dist files. It extracts
    the core XML data and generates a structured JSON analysis.
    """

    def __init__(self, file_path, debug=False):
        self.file_path = file_path
        self.debug = debug
        self.xml_root = None
        self.analysis_title = "Niagara Analysis"

    def _get_value_from_node(self, node):
        if 'v' in node.attrib:
            return node.attrib['v']
        if node.text and node.text.strip():
            return node.text.strip()
        return None

    def list_archive_contents(self):
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"The specified file does not exist: {self.file_path}")
        if not zipfile.is_zipfile(self.file_path):
            raise ValueError(f"File is not a valid archive: {self.file_path}")
        with zipfile.ZipFile(self.file_path, 'r') as archive:
            return archive.namelist()

    def _process_file(self):
        if self.xml_root:
            return
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"The specified file does not exist: {self.file_path}")
        if self.file_path.endswith('.bog'):
            self.analysis_title = "Niagara BOG File Analysis"
            self._parse_bog_file()
        elif self.file_path.endswith('.dist'):
            self.analysis_title = "Niagara Station Analysis"
            self._parse_dist_file()
        else:
            raise ValueError("Unsupported file type. Please provide a .bog or .dist file.")

    def _get_xml_content_from_bytes(self, xml_bytes):
        try:
            return xml_bytes.decode('utf-8-sig')
        except UnicodeDecodeError:
            return xml_bytes.decode('latin-1')

    def _parse_bog_file(self):
        try:
            with zipfile.ZipFile(self.file_path, 'r') as bog_zip:
                xml_bytes = bog_zip.read('file.xml')
                xml_content = self._get_xml_content_from_bytes(xml_bytes)
                self.xml_root = ET.fromstring(xml_content)
        except zipfile.BadZipFile:
            raise ValueError(f"File is not a valid .bog (ZIP) file: {self.file_path}")
        except KeyError:
            raise ValueError("The .bog file does not contain a 'file.xml' entry.")

    def _parse_dist_file(self):
        if not zipfile.is_zipfile(self.file_path):
            raise ValueError(f"File is not a valid .dist (ZIP) file or may be corrupted: {self.file_path}")

        with zipfile.ZipFile(self.file_path, 'r') as dist_zip:
            config_bog_path = None
            pattern = re.compile(r"niagara_user_home/stations/[^/]+/config\.bog$", re.IGNORECASE)

            for path in dist_zip.namelist():
                if pattern.search(path):
                    config_bog_path = path
                    break

            if not config_bog_path:
                raise FileNotFoundError("Could not find a main config.bog inside the .dist archive.")

            with dist_zip.open(config_bog_path) as config_bog_file:
                config_bog_data = config_bog_file.read()

            with zipfile.ZipFile(io.BytesIO(config_bog_data), 'r') as config_bog_zip:
                if 'file.xml' not in config_bog_zip.namelist():
                    raise FileNotFoundError("file.xml not found inside config.bog.")
                xml_bytes = config_bog_zip.read('file.xml')
                xml_content = self._get_xml_content_from_bytes(xml_bytes)
                self.xml_root = ET.fromstring(xml_content)

            self.analysis_title = "Niagara Station Analysis (config.bog)"

    def _extract_all_components(self, start_element):
        components = []
        handle_to_name_map = {}

        for comp_element in start_element.findall('.//p[@h]'):
            comp_name = comp_element.get('n')
            comp_handle = comp_element.get('h')

            if comp_name and comp_handle:
                handle_to_name_map[f"h:{comp_handle}"] = comp_name

                component = {
                    'name': comp_name,
                    'type': comp_element.get('t'),
                    'links': [],
                    'properties': {}
                }

                for link_element in comp_element.findall('.//p[@t="b:Link"]'):
                    link_data = {
                        'source_ord': link_element.find('p[@n="sourceOrd"]').get('v'),
                        'source_slot': link_element.find('p[@n="sourceSlotName"]').get('v'),
                        'target_slot': link_element.find('p[@n="targetSlotName"]').get('v')
                    }
                    component['links'].append(link_data)

                for prop in comp_element.findall("p"):
                    prop_name = prop.attrib.get("n")
                    prop_val = self._get_value_from_node(prop)
                    if not prop_name:
                        continue
                    component['properties'][prop_name] = prop_val

                components.append(component)

        return components, handle_to_name_map

    def generate_analysis_data(self):
        self._process_file()
        if self.xml_root is None:
            return None
        components, handle_map = self._extract_all_components(self.xml_root)
        return {
            'title': self.analysis_title,
            'source': os.path.basename(self.file_path),
            'components': components,
            'handle_map': handle_map
        }

    def save_analysis_to_file(self, analysis_data, output_file):
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(analysis_data, f, indent=2)
        print(f"Station analysis saved to {output_file}")