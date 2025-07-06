# src/dist_explorer.py
import zipfile
import os
import io
import re
from .bog_parser import BogParser

class DistExplorer:
    """
    Explores a Niagara .dist station backup file to find and parse the main
    config.bog, creating a structured representation of the station.
    """

    def __init__(self, dist_file_path, debug=False):
        self.dist_file_path = dist_file_path
        self.debug = debug
        if not os.path.exists(dist_file_path):
            raise FileNotFoundError(f"The specified file does not exist: {dist_file_path}")
        if not zipfile.is_zipfile(dist_file_path):
            raise ValueError(f"File is not a valid .dist (ZIP) file or may be corrupted: {dist_file_path}")
        
        with zipfile.ZipFile(self.dist_file_path, 'r') as dist_zip:
            self.file_list = dist_zip.namelist()

    def list_all_files(self):
        """Returns a list of all files and folders inside the .dist archive."""
        return self.file_list

    def analyze_station(self):
        """
        Analyzes the station by finding and parsing the main config.bog.

        Returns:
            A dictionary representing the parsed station config, or None.
        """
        config_bog_path = self._find_config_bog_path()
        
        if config_bog_path:
            if self.debug:
                print(f"Primary target found: {config_bog_path}")
            return self._parse_station_config_from_dist(config_bog_path)
        
        if self.debug:
            print("Could not find a primary config.bog in the archive.")
        return None

    def _find_config_bog_path(self):
        """Finds the canonical path to the main station config.bog file."""
        pattern = re.compile(r"niagara_user_home/stations/([^/]+)/config\.bog$")
        for path in self.file_list:
            if pattern.search(path):
                return path
        return None

    def _parse_station_config_from_dist(self, bog_path_in_zip):
        """Helper to parse the main config.bog file from within the DIST archive."""
        with zipfile.ZipFile(self.dist_file_path, 'r') as dist_zip:
            try:
                # Read the bytes of the nested config.bog file
                config_bog_bytes = dist_zip.read(bog_path_in_zip)
                
                # Create a file-like object from the bytes for the BogParser
                bog_file_like_object = io.BytesIO(config_bog_bytes)
                
                # Use our existing BogParser, which knows how to handle this format
                parser = BogParser(bog_file_like_object, debug=self.debug)
                
                station_root = parser.root 
                if station_root is not None:
                    components, handle_map = self._extract_all_components(station_root)
                    station_name_match = re.search(r"stations/([^/]+)/config", bog_path_in_zip)
                    station_name = station_name_match.group(1) if station_name_match else "UnknownStation"
                    
                    return {
                        'path': bog_path_in_zip,
                        'station_name': station_name,
                        'components': components,
                        'handle_map': handle_map
                    }
            except Exception as e:
                if self.debug:
                    print(f"  -> Could not parse {bog_path_in_zip}: {e}")
        return None

    def _extract_all_components(self, start_element):
        """Recursively extracts all components and their links from the XML tree."""
        components = []
        handle_to_name_map = {}

        for comp_element in start_element.findall('.//p[@h]'): # Find all elements with a handle
            comp_name = comp_element.get('n')
            comp_handle = comp_element.get('h')
            if comp_name and comp_handle:
                handle_to_name_map[f"h:{comp_handle}"] = comp_name
                component = {
                    'name': comp_name,
                    'type': comp_element.get('t'),
                    'links': []
                }
                for link_element in comp_element.findall('.//p[@t="b:Link"]'):
                    link_data = {
                        'source_ord': link_element.find('p[@n="sourceOrd"]').get('v'),
                        'source_slot': link_element.find('p[@n="sourceSlotName"]').get('v'),
                        'target_slot': link_element.find('p[@n="targetSlotName"]').get('v')
                    }
                    component['links'].append(link_data)
                components.append(component)
        return components, handle_to_name_map

    def save_analysis_to_file(self, station_data, output_file):
        """
        Saves the structured station analysis to a human-readable text file
        perfect for LLM context.
        """
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# Niagara Station Analysis\n")
            f.write(f"Source: {os.path.basename(self.dist_file_path)}\n")
            f.write(f"Station Name: {station_data['station_name']}\n")
            f.write(f"Config Path: {station_data['path']}\n")
            f.write("="*40 + "\n\n")

            handle_map = station_data['handle_map']

            for comp in station_data['components']:
                f.write(f"## Component: {comp['name']} (Type: {comp['type']})\n")
                if comp['links']:
                    f.write("  Links To This Component:\n")
                    for link in comp['links']:
                        source_name = handle_map.get(link['source_ord'], f"Unresolved Handle ({link['source_ord']})")
                        f.write(f"    - From: {source_name} (Slot: {link['source_slot']}) -> To: {comp['name']} (Slot: {link['target_slot']})\n")
                f.write("\n")
        
        print(f"Station analysis saved to {output_file}")