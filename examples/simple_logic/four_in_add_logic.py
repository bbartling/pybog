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

    # 1. Initialize the builder
    builder = BogFolderBuilder("AutoLayoutFourInputAdder")

    # 2. Register all TOP-LEVEL components.
    # These are the clean inputs and the final output the user will interact with.
    # --- Inputs ---
    builder.add_numeric_writable(name="Input1", default_value=10.0)
    builder.add_numeric_writable(name="Input2", default_value=20.0)
    builder.add_numeric_writable(name="Input3", default_value=30.0)
    builder.add_numeric_writable(name="Input4", default_value=40.0)
    
    # --- Output ---
    builder.add_numeric_writable(name="Sum")


    # TUTORIAL: HOW TO USE SUB-FOLDERS
    # Even for a single logic block, we can use a sub-folder to keep the
    # top-level wiresheet as clean as possible.

    # STEP 1: Start the sub-folder "sandbox".
    # To see the logic flat for debugging, you can simply comment out this line.
    builder.start_sub_folder("CalculationLogic")

    # --- Logic Block ---
    # This 'Add' component is now created inside the "CalculationLogic" folder.
    builder.add_component(comp_type="kitControl:Add", name="Add")

    # STEP 2: End the sub-folder "sandbox".
    # To see the logic flat for debugging, you can simply comment out this line.
    builder.end_sub_folder()


    # 3. Register all links.
    # No changes are needed here. The builder will automatically create proxies
    # for all links that cross the boundary into or out of "CalculationLogic".
    builder.add_link("Input1", "out", "Add", "inA")
    builder.add_link("Input2", "out", "Add", "inB")
    builder.add_link("Input3", "out", "Add", "inC")
    builder.add_link("Input4", "out", "Add", "inD")
    builder.add_link("Add", "out", "Sum", "in16")

    # 4. Save the file. This triggers the layout calculation and file writing.
    bog_filename = f"{script_filename}.bog"
    output_path = os.path.join(args.output_dir, bog_filename)
    os.makedirs(args.output_dir, exist_ok=True)
    builder.save(output_path)
    print(f"\nSuccessfully created Niagara .bog file at: {output_path}")

if __name__ == "__main__":
    main()
