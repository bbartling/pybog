# examples/main_analyzer.py
import sys
import os
import argparse

# Add the 'src' directory to the Python path so we can import the Analyzer
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.analyzer import Analyzer


def main():
    # Set up the command-line argument parser with helpful descriptions and examples
    parser = argparse.ArgumentParser(
        description="Analyze a Niagara .bog or .dist file and create a human-readable summary.",
        epilog="Examples:\n"
        "  python examples/main_analyzer.py examples/ClgControlLogic.bog -o logic_analysis.txt\n"
        "  python examples/main_analyzer.py examples/backup_Diggs_RTU9.dist -o C:\\Users\\YourUser\\Desktop\\station_analysis.txt",
    )
    parser.add_argument("file", help="Path to the .bog or .dist file to analyze.")
    parser.add_argument(
        "-o", "--output", default="analysis.txt", help="Output file for the analysis."
    )
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="Enable debug mode for verbose output.",
    )
    parser.add_argument(
        "-l",
        "--list-files",
        action="store_true",
        help="List all files in the archive and exit.",
    )

    args = parser.parse_args()

    try:
        print(f"--- Starting analysis of {args.file} ---")

        analyzer = Analyzer(args.file, debug=args.debug)

        if args.list_files:
            files = analyzer.list_archive_contents()
            print(f"--- Archive Contents of {args.file} ---")
            for f in files:
                print(f" - {f}")
            print("--- End of List ---")

        # If not just listing, continue with full analysis
        analysis_data = analyzer.generate_analysis_data()

        if analysis_data:
            analyzer.save_analysis_to_file(analysis_data, args.output)
            print("\n--- Analysis Complete ---")
            print(
                f"Full details saved to '{args.output}'. This file can be used for LLM context."
            )
        else:
            print("\nAnalysis failed: Could not extract any valid data from the file.")

    except (ValueError, FileNotFoundError) as e:
        print(f"\n--- [ERROR] ---")
        print(f"Error: {e}")
    except Exception as e:
        print(f"\n--- [UNEXPECTED ERROR] ---")
        print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    main()
