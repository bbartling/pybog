# examples/main_parser.py
import sys
import os

# This allows the script to find the 'src' directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.bog_parser import BogParser

# --- How to Run ---
# python examples/main_parser.py examples/YourBogFileName.bog
# python examples/main_parser.py examples/YourBogFileName.bog --debug
# ------------------

def main():
    # 1. Get command line arguments
    args = sys.argv[1:]
    if not args:
        print("Usage: python examples/main_parser.py <path_to_bog_file> [--debug]")
        sys.exit(1)
        
    bog_file_path = args[0]
    debug_mode = "--debug" in args or "-d" in args

    try:
        # 2. Create a parser instance with the provided file path and debug flag
        parser = BogParser(bog_file_path, debug=debug_mode)
        print(f"--- Parsing file: {bog_file_path} ---")

        # 3. Find the main logic folder dynamically
        logic_folder = parser.find_component('./p[@t="b:UnrestrictedFolder"]/p[@t="b:Folder"]')
        
        if logic_folder is not None:
            folder_name = logic_folder.get('n', 'Unnamed Folder')
            print(f"\nFound main logic folder: '{folder_name}'")
            print(f"\n--- Components inside '{folder_name}' ---")
            
            components = parser.list_slots(logic_folder)
            if not components:
                print("  No components found in this folder.")
            
            for comp in components:
                if comp['name']:
                     print(f"  - Component Name: {comp['name']}, Type: {comp['type']}")
        else:
            print("\nCould not find a main logic folder (b:Folder) inside the BOG file.")
            
        # 4. If in debug mode, print the full tree
        if debug_mode:
            print("\n--- Raw XML Tree Structure (Debug Mode) ---")
            parser.print_tree()

    except (ValueError, FileNotFoundError) as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
