"""
Demonstrates the `kitControl:NumericSelect` component, which acts as a
multiplexer. It takes five different numeric inputs (inA through inE) and
a separate numeric 'select' input. The value of the 'select' input
determines which of the five inputs is passed through to the output. For
example, a selector value of 1.0 outputs inA, 2.0 outputs inB, and so on.
"""

import sys
import os
import argparse

from bog_builder import BogFolderBuilder


def main():
    """
    This script builds a simple test case for the NumericSelect component
    to verify the special StatusNumericToStatusEnum conversion link.
    """
    parser = argparse.ArgumentParser(
        description="Build a .bog file to test the NumericSelect component."
    )
    parser.add_argument(
        "-o",
        "--output_dir",
        default="examples",
        help="Output directory for the .bog file.",
    )
    args = parser.parse_args()

    script_filename = os.path.basename(__file__).replace(".py", "")

    builder = BogFolderBuilder("NumericSelectTest")

    print("Creating components...")


    # --- Inputs ---
    builder.add_numeric_writable("Input_A", default_value=100.0)
    builder.add_numeric_writable("Input_B", default_value=200.0)
    builder.add_numeric_writable("Input_C", default_value=300.0)
    builder.add_numeric_writable("Input_D", default_value=400.0)
    builder.add_numeric_writable("Input_E", default_value=500.0)

    builder.add_numeric_writable("Selector", default_value=1.0)

    builder.add_numeric_select("MySelect")

    # --- Output ---
    builder.add_numeric_writable("Selected_Value")

    print("Wiring components...")

    builder.add_link("Input_A", "out", "MySelect", "inA")
    builder.add_link("Input_B", "out", "MySelect", "inB")
    builder.add_link("Input_C", "out", "MySelect", "inC")
    builder.add_link("Input_D", "out", "MySelect", "inD")
    builder.add_link("Input_E", "out", "MySelect", "inE")

    builder.add_link("Selector", "out", "MySelect", "select")

    builder.add_link("MySelect", "out", "Selected_Value", "in16")

    bog_filename = f"{script_filename}.bog"
    output_path = os.path.join(args.output_dir, bog_filename)
    os.makedirs(args.output_dir, exist_ok=True)
    builder.save(output_path)
    print(f"\nSuccessfully created Niagara .bog file at: {output_path}")
    print("You can now test this file in Niagara Workbench.")


if __name__ == "__main__":
    main()
