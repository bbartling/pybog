import sys
import os
import argparse

# Add the 'src' directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.bog_builder import BogFolderBuilder

def main():
    parser = argparse.ArgumentParser(description="Build a complex, multi-algorithm .bog file with the simple API.")
    parser.add_argument("-o", "--output_dir", default="examples", help="Output directory.")
    args = parser.parse_args()

    builder = BogFolderBuilder("TieredLogicTest")

    input_names = []
    for i in range(1, 12):
        name = f"Input{i}"
        builder.add_numeric_writable(name, default_value=i * 10.0)
        input_names.append(name)

    print("INPUT NAMES", input_names)

    # Use single high-level API calls
    builder.add_reduction_block("Average", "Avg_Final", input_names)
    builder.add_reduction_block("Minimum", "Min_Final", input_names)
    builder.add_reduction_block("Maximum", "Max_Final", input_names)

    output_path = os.path.join(args.output_dir, "mod_avg_min_max.bog")
    os.makedirs(args.output_dir, exist_ok=True)
    builder.save(output_path)
    print(f"Successfully created {output_path}")

if __name__ == "__main__":
    main()