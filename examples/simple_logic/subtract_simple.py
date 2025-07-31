import sys
import os
import argparse

# Add the 'src' directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
# Make sure you are importing the new builder with sub-folder capabilities
from src.bog_builder_new import BogFolderBuilder


def main():
    """
    This script uses the BogFolderBuilder to create a wiresheet that
    subtracts one number from another (Input_A - Input_B).
    """
    parser = argparse.ArgumentParser(
        description="Build a subtraction logic .bog file with automatic layout."
    )
    parser.add_argument(
        "-o", "--output_dir", default="examples", help="Output directory."
    )
    args = parser.parse_args()

    script_filename = os.path.basename(__file__).replace(".py", "")

    # 1. Initialize the builder
    builder = BogFolderBuilder("SubtractionLogic")

    # 2. Register all TOP-LEVEL components.
    # These are the clean inputs and the final output the user will interact with.
    # --- Inputs ---
    builder.add_numeric_writable(name="Input_A", default_value=100.0)
    builder.add_numeric_writable(name="Input_B", default_value=40.0)
    
    # --- Output ---
    builder.add_numeric_writable(name="Difference")


    # TUTORIAL: HOW TO USE SUB-FOLDERS
    # Even for a single logic block, we can use a sub-folder to keep the
    # top-level wiresheet as clean as possible.

    # STEP 1: Start the sub-folder "sandbox".
    # To see the logic flat for debugging, you can simply comment out this line.
    builder.start_sub_folder("CalculationLogic")

    # --- Logic Block ---
    # This 'Subtract' component is now created inside the "CalculationLogic" folder.
    builder.add_component(comp_type="kitControl:Subtract", name="Subtract")

    # STEP 2: End the sub-folder "sandbox".
    # To see the logic flat for debugging, you can simply comment out this line.
    builder.end_sub_folder()


    # 3. Register all links. This is how the layout is determined.
    # No changes are needed here. The builder will automatically create proxies
    # for all links that cross the boundary into or out of "CalculationLogic".
    builder.add_link("Input_A", "out", "Subtract", "inA")
    builder.add_link("Input_B", "out", "Subtract", "inB")
    builder.add_link("Subtract", "out", "Difference", "in16")

    # 4. Save the file. This triggers the layout calculation and file writing.
    bog_filename = f"{script_filename}.bog"
    output_path = os.path.join(args.output_dir, bog_filename)
    os.makedirs(args.output_dir, exist_ok=True)
    builder.save(output_path)
    print(f"\nSuccessfully created Niagara .bog file at: {output_path}")


if __name__ == "__main__":
    main()
