import sys
import os
import argparse

# Add the 'src' directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.bog_builder import BogFolderBuilder

def main():
    """
    This script uses the BogFolderBuilder to create a wiresheet that
    subtracts one number from another (Input_A - Input_B).
    """
    parser = argparse.ArgumentParser(description="Build a subtraction logic .bog file with automatic layout.")
    parser.add_argument("-o", "--output_dir", default="examples", help="Output directory.")
    args = parser.parse_args()

    # 1. Initialize the builder
    builder = BogFolderBuilder("SubtractionLogic")

    # 2. Register all components.
    # The builder's layout engine will automatically place them.
    builder.add_numeric_writable(name="Input_A", default_value=100.0)
    builder.add_numeric_writable(name="Input_B", default_value=40.0)
    builder.add_component(comp_type="kitControl:Subtract", name="Subtract")
    builder.add_numeric_writable(name="Difference")

    # 3. Register all links. This is how the layout is determined.
    builder.add_link("Input_A", "out", "Subtract", "inA")
    builder.add_link("Input_B", "out", "Subtract", "inB")
    builder.add_link("Subtract", "out", "Difference", "in16")

    # 4. Save the file. This triggers the layout calculation and file writing.
    output_path = os.path.join(args.output_dir, "subtract_logic_auto.bog")
    os.makedirs(args.output_dir, exist_ok=True)
    builder.save(output_path)
    print(f"Successfully created {output_path}")

if __name__ == "__main__":
    main()
