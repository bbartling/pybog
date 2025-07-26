import sys
import os
import argparse

# Add the 'src' directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.bog_builder import BogFolderBuilder

def main():
    parser = argparse.ArgumentParser(description="Build a 4-input adder .bog file with automatic layout.")
    parser.add_argument("-o", "--output_dir", default="examples", help="Output directory.")
    args = parser.parse_args()

    # 1. Initialize the builder
    builder = BogFolderBuilder("AutoLayoutFourInputAdder")

    # 2. Register all components. The builder will handle the layout.
    builder.add_numeric_writable(name="Input1", default_value=10.0)
    builder.add_numeric_writable(name="Input2", default_value=20.0)
    builder.add_numeric_writable(name="Input3", default_value=30.0)
    builder.add_numeric_writable(name="Input4", default_value=40.0)
    builder.add_component(comp_type="kitControl:Add", name="Add")
    builder.add_numeric_writable(name="Sum")

    # 3. Register all links. This is CRITICAL for the layout engine.
    builder.add_link("Input1", "out", "Add", "inA")
    builder.add_link("Input2", "out", "Add", "inB")
    builder.add_link("Input3", "out", "Add", "inC")
    builder.add_link("Input4", "out", "Add", "inD")
    builder.add_link("Add", "out", "Sum", "in16")

    # 4. Save the file. This triggers the layout calculation and file writing.
    output_path = os.path.join(args.output_dir, "4_input_adder_auto.bog")
    os.makedirs(args.output_dir, exist_ok=True)
    builder.save(output_path)
    print(f"Successfully created {output_path}")

if __name__ == "__main__":
    main()
