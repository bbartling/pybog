import sys
import os
import argparse

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.bog_builder import BogFolderBuilder


def main():
    parser = argparse.ArgumentParser(
        description="Build a Boolean logic with NumericSwitch .bog file."
    )
    parser.add_argument(
        "-o", "--output_dir", default="examples", help="Output directory."
    )
    args = parser.parse_args()

    builder = BogFolderBuilder("BooleanLogicNumericSwitch", debug=True)

    # Inputs
    builder.add_numeric_writable("Input_A", default_value=100.0)
    builder.add_numeric_writable("Input_B", default_value=40.0)
    builder.add_boolean_writable("BooleanWritable", default_value=False)

    # Logic Components
    builder.add_component("kitControl:Add", "Add")
    builder.add_component("kitControl:Subtract", "Subtract")
    builder.add_component("kitControl:Equal", "Equal")
    builder.add_numeric_switch("NumericSwitch")

    # Output
    builder.add_numeric_writable("Output")

    # Wiring:
    # Add: Input_A + Input_B
    builder.add_link("Input_A", "out", "Add", "inA")
    builder.add_link("Input_B", "out", "Add", "inB")

    # Subtract: Input_A - Input_B
    builder.add_link("Input_A", "out", "Subtract", "inA")
    builder.add_link("Input_B", "out", "Subtract", "inB")

    # Equal: BooleanWritable == True? (compares to 1.00 constant)
    builder.add_link("BooleanWritable", "out", "Equal", "inA")
    # Constant for Equal (1.0 True)
    const_true = "Const_True"
    builder.add_numeric_writable(const_true, default_value=1.0)
    builder.add_link(const_true, "out", "Equal", "inB")

    # NumericSwitch wiring
    builder.add_link("Equal", "out", "NumericSwitch", "inSwitch")
    builder.add_link("Add", "out", "NumericSwitch", "inTrue")
    builder.add_link("Subtract", "out", "NumericSwitch", "inFalse")

    # Final Output
    builder.add_link("NumericSwitch", "out", "Output", "in16")

    # Save file
    output_path = os.path.join(args.output_dir, "boolean_numeric_switch.bog")
    os.makedirs(args.output_dir, exist_ok=True)
    builder.save(output_path)
    print(f"Successfully created {output_path}")


if __name__ == "__main__":
    main()
