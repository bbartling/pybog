import sys
import os
import argparse

from bog_builder import BogFolderBuilder


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

    # === Inputs ===
    builder.add_numeric_writable("Input_A", default_value=100.0)
    builder.add_numeric_writable("Input_B", default_value=40.0)
    builder.add_boolean_writable("BooleanWritable", default_value=False)

    # === Output ===
    builder.add_numeric_writable("Output")

    builder.start_sub_folder("CalculationLogic")

    builder.add_component("kitControl:Add", "Add")
    builder.add_component("kitControl:Subtract", "Subtract")
    builder.add_component("kitControl:Equal", "Equal")
    builder.add_numeric_switch("NumericSwitch")

    builder.add_numeric_writable("Const_True", default_value=1.0)

    builder.end_sub_folder()

    builder.add_link("Input_A", "out", "Add", "inA")
    builder.add_link("Input_B", "out", "Add", "inB")
    builder.add_link("Input_A", "out", "Subtract", "inA")
    builder.add_link("Input_B", "out", "Subtract", "inB")

    builder.add_link("BooleanWritable", "out", "Equal", "inA")
    builder.add_link("Const_True", "out", "Equal", "inB")

    builder.add_link("Equal", "out", "NumericSwitch", "inSwitch")
    builder.add_link("Add", "out", "NumericSwitch", "inTrue")
    builder.add_link("Subtract", "out", "NumericSwitch", "inFalse")

    builder.add_link("NumericSwitch", "out", "Output", "in16")

    bog_filename = f"{script_filename}.bog"
    output_path = os.path.join(args.output_dir, bog_filename)
    os.makedirs(args.output_dir, exist_ok=True)
    builder.save(output_path)
    print(f"\nSuccessfully created Niagara .bog file at: {output_path}")


if __name__ == "__main__":
    main()
