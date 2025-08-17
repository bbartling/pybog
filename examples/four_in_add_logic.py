import sys
import os
import argparse

# Add the 'src' directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
# Make sure you are importing the new builder with sub-folder capabilities
from src.bog_builder_new import BogFolderBuilder


def main():
    parser = argparse.ArgumentParser(
        description="Build a 4-input adder .bog file with automatic layout."
    )
    parser.add_argument(
        "-o", "--output_dir", default="examples", help="Output directory."
    )
    args = parser.parse_args()

    script_filename = os.path.basename(__file__).replace(".py", "")

    builder = BogFolderBuilder("AutoLayoutFourInputAdder")

    # --- Inputs ---
    builder.add_numeric_writable(name="Input1", default_value=10.0)
    builder.add_numeric_writable(name="Input2", default_value=20.0)
    builder.add_numeric_writable(name="Input3", default_value=30.0)
    builder.add_numeric_writable(name="Input4", default_value=40.0)
    
    # --- Output ---
    builder.add_numeric_writable(name="Sum")
    builder.start_sub_folder("CalculationLogic")

    builder.add_component(comp_type="kitControl:Add", name="Add")

    builder.end_sub_folder()

    builder.add_link("Input1", "out", "Add", "inA")
    builder.add_link("Input2", "out", "Add", "inB")
    builder.add_link("Input3", "out", "Add", "inC")
    builder.add_link("Input4", "out", "Add", "inD")
    builder.add_link("Add", "out", "Sum", "in16")

    bog_filename = f"{script_filename}.bog"
    output_path = os.path.join(args.output_dir, bog_filename)
    os.makedirs(args.output_dir, exist_ok=True)
    builder.save(output_path)
    print(f"\nSuccessfully created Niagara .bog file at: {output_path}")

if __name__ == "__main__":
    main()
