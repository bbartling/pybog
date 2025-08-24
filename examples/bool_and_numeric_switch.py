"""
Algorithm demos boolean and numeric switch
and bool and numeric constants declorations.
Boolean-controlled numeric mode switch:
  - BooleanWritable = true  -> Output = A + B
  - BooleanWritable = false -> Output = A - B
Uses BOTH BooleanSwitch (your new helper) and NumericSwitch.
"""

import os
import argparse
from bog_builder import BogFolderBuilder


def main():
    parser = argparse.ArgumentParser(
        description="Boolean→Numeric switching demo (.bog)"
    )
    parser.add_argument(
        "-o", "--output_dir", default="examples", help="Output directory."
    )
    args = parser.parse_args()

    script_filename = os.path.basename(__file__).replace(".py", "")
    b = BogFolderBuilder("BooleanLogicNumericSwitch", debug=True)

    # Inputs/Output
    b.add_component("kitControl:NumericConst", "Input_A", properties={"value": 100.05})
    b.add_component("kitControl:NumericConst", "Input_B", properties={"value": 42.2})

    b.add_boolean_writable("BooleanWritable", default_value=False)
    b.add_numeric_writable("Output")

    # Logic subfolder
    b.start_sub_folder("CalculationLogic")
    b.add_component("kitControl:Add", "Add")
    b.add_component("kitControl:Subtract", "Subtract")
    b.add_numeric_switch("NumericSwitch")
    b.add_boolean_switch("ModeSwitch")  # <-- your new helper
    b.add_component("kitControl:BooleanConst", "ConstTrue", properties={"value": True})
    b.add_component(
        "kitControl:BooleanConst", "ConstFalse", properties={"value": False}
    )
    b.end_sub_folder()

    # Wire math
    b.add_link("Input_A", "out", "Add", "inA")
    b.add_link("Input_B", "out", "Add", "inB")
    b.add_link("Input_A", "out", "Subtract", "inA")
    b.add_link("Input_B", "out", "Subtract", "inB")

    # Boolean path: BooleanWritable → BooleanSwitch → NumericSwitch.inSwitch
    b.add_link("BooleanWritable", "out", "ModeSwitch", "inSwitch")
    b.add_link("ConstTrue", "out", "ModeSwitch", "inTrue")
    b.add_link("ConstFalse", "out", "ModeSwitch", "inFalse")
    b.add_link("ModeSwitch", "out", "NumericSwitch", "inSwitch")

    # Numeric selection
    b.add_link("Add", "out", "NumericSwitch", "inTrue")
    b.add_link("Subtract", "out", "NumericSwitch", "inFalse")
    b.add_link("NumericSwitch", "out", "Output", "in16")

    # Save
    bog_filename = f"{script_filename}.bog"
    output_path = os.path.join(args.output_dir, bog_filename)
    os.makedirs(args.output_dir, exist_ok=True)
    b.save(output_path)
    print(f"\nSuccessfully created Niagara .bog file at: {output_path}")


if __name__ == "__main__":
    main()
