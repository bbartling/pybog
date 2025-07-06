# examples/main_dist_explorer.py
import sys
import os
import argparse

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.dist_explorer import DistExplorer

def main():
    parser = argparse.ArgumentParser(
        description="Explore a Niagara .dist station backup and analyze its contents.",
        epilog="Example: python examples/main_dist_explorer.py examples/backup_Diggs_RTU9.dist -o diggs_analysis.txt"
    )
    parser.add_argument("file", help="Path to the .dist file to explore.")
    parser.add_argument("-o", "--output", default="station_analysis.txt", help="Output file for the analysis.")
    parser.add_argument("-l", "--list-files", action="store_true", help="List all files in the .dist archive and exit.")
    parser.add_argument("-d", "--debug", action="store_true", help="Enable debug mode for verbose output.")
    
    args = parser.parse_args()

    try:
        print(f"--- Opening {args.file} ---")
        explorer = DistExplorer(args.file, debug=args.debug)

        if args.list_files:
            print("\n--- Files found in archive ---")
            for file_name in explorer.list_all_files():
                print(file_name)
            return

        # Analyze the station to find the main config.bog
        station_data = explorer.analyze_station()
        
        if not station_data:
            print("\nAnalysis complete, but a main config.bog was not found in the .dist file.")
            return

        # Save the analysis to a text file
        explorer.save_analysis_to_file(station_data, args.output)
        
        print("\n--- Analysis Complete ---")
        print(f"Successfully parsed the main station configuration.")
        print(f"Full details saved to '{args.output}'. This file can be used for LLM context.")

    except (ValueError, FileNotFoundError) as e:
        print(f"\n--- [CRASH LOG] ---")
        print(f"Error: {e}")
        if isinstance(e, FileNotFoundError):
            print("Please check that the file exists and the path is correct.")
            print("Remember to include the 'examples/' prefix if the file is in that folder.")
        else:
            print("This usually means the file is not a valid station backup or it may be corrupted.")

    except Exception as e:
        print(f"\n--- [CRASH LOG] ---")
        print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    main()
