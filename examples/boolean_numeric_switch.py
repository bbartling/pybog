import sys
import os
import argparse

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
# Make sure you are importing the new builder with sub-folder capabilities
from src.bog_builder_new import BogFolderBuilder


def main():
    parser = argparse.ArgumentParser(
        description="Build a Boolean logic with NumericSwitch .bog file."
    )
    parser.add_argument(
        "-o", "--output_dir", default="examples", help="Output directory."
    )
    args = parser.parse_args()

    script_filename = os.path.basename(__file__).replace(".py", "")

    builder = BogFolderBuilder("BooleanLogicNumericSwitch", debug=True)

    # 1. Define all TOP-LEVEL components first.
    # These are the inputs and outputs the user will directly interact with.
    # === Inputs ===
    builder.add_numeric_writable("Input_A", default_value=100.0)
    builder.add_numeric_writable("Input_B", default_value=40.0)
    builder.add_boolean_writable("BooleanWritable", default_value=False)

    # === Output ===
    builder.add_numeric_writable("Output")


    # TUTORIAL: HOW TO USE SUB-FOLDERS
    # We will place all the intermediate logic blocks (Add, Subtract, Equal, Switch)
    # inside a single sub-folder to keep the main wiresheet clean.

    # STEP 1: Start the sub-folder "sandbox".
    # To see the logic flat for debugging, you can simply comment out this line.
    builder.start_sub_folder("CalculationLogic")

    # --- Logic Components ---
    # These components are now created inside the "CalculationLogic" folder.
    builder.add_component("kitControl:Add", "Add")
    builder.add_component("kitControl:Subtract", "Subtract")
    builder.add_component("kitControl:Equal", "Equal")
    builder.add_numeric_switch("NumericSwitch")
    # Note: Even this writable, used as a constant, is part of the logic,
    # so it should also be created inside the sub-folder.
    builder.add_numeric_writable("Const_True", default_value=1.0)

    # STEP 2: End the sub-folder "sandbox".
    # To see the logic flat for debugging, you can simply comment out this line.
    builder.end_sub_folder()


    # 3. Register all links.
    # No changes are needed here. The builder will automatically create proxies
    # for all links that cross the boundary into or out of "CalculationLogic".

    # Wiring for math blocks (inside the sub-folder)
    builder.add_link("Input_A", "out", "Add", "inA")
    builder.add_link("Input_B", "out", "Add", "inB")
    builder.add_link("Input_A", "out", "Subtract", "inA")
    builder.add_link("Input_B", "out", "Subtract", "inB")

    # Wiring for the comparison (inside the sub-folder)
    builder.add_link("BooleanWritable", "out", "Equal", "inA")
    builder.add_link("Const_True", "out", "Equal", "inB")

    # Wiring for the final switch (inside the sub-folder)
    builder.add_link("Equal", "out", "NumericSwitch", "inSwitch")
    builder.add_link("Add", "out", "NumericSwitch", "inTrue")
    builder.add_link("Subtract", "out", "NumericSwitch", "inFalse")

    # Final Output link (from the sub-folder to the top-level output)
    builder.add_link("NumericSwitch", "out", "Output", "in16")

    # 4. Save file
    bog_filename = f"{script_filename}.bog"
    output_path = os.path.join(args.output_dir, bog_filename)
    os.makedirs(args.output_dir, exist_ok=True)
    builder.save(output_path)
    print(f"\nSuccessfully created Niagara .bog file at: {output_path}")


if __name__ == "__main__":
    main()
