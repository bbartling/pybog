"""
multivibrator_link_test.py

A minimal "smoke test" to verify the dynamic linking of a numeric value
to the 'Period' property of a kitControl:MultiVibrator component.

This script is designed to confirm that the fixes made to the BogFolderBuilder
correctly generate the required dual-link XML structure with the necessary
type converters.

Algorithm:
1.  A NumericWritable ('UpdateSeconds') provides a user-configurable input.
2.  This value is multiplied by 1000 to convert it to milliseconds.
3.  The resulting millisecond value is linked to the 'Period' of the MultiVibrator.
4.  The 'out' of the MultiVibrator is linked to a BooleanWritable ('PulseOutput')
    to provide a clear visual indication of its operation.
"""

import os
import argparse
from bog_builder import BogFolderBuilder


def main():
    """
    Main function to build and save the .bog file.
    """
    parser = argparse.ArgumentParser(
        description="Build a .bog file to smoke test dynamic linking to a MultiVibrator's Period."
    )
    parser.add_argument(
        "-o",
        "--output_dir",
        default="examples",
        help="Output directory for the .bog file.",
    )
    args = parser.parse_args()

    script_filename = os.path.basename(__file__).replace(".py", "")
    builder = BogFolderBuilder("MultiVibratorLinkTest", debug=True)

    print("--- Creating Components for MultiVibrator Test ---")

    # --- Inputs ---
    # This is the knob you can turn in Workbench to change the period.
    builder.add_numeric_writable("UpdateSeconds", default_value=5.0)

    # --- Output ---
    # This boolean will pulse on and off so you can see the result.
    builder.add_boolean_writable("PulseOutput")

    # A constant for converting seconds to milliseconds.
    builder.add_component(
        "kitControl:NumericConst", "Const_1000", properties={"value": 1000.0}
    )

    # The block that performs the ms calculation.
    builder.add_component("kitControl:Multiply", "Update_ms_Calc")

    # Update Timer
    default_period_ms = "1000"

    builder.add_component(
        "kitControl:MultiVibrator",
        "TestMultiVibrator",
        properties={"period": default_period_ms},
    )
    print("\n--- Wiring Components ---")

    # Wire the seconds-to-milliseconds calculation
    builder.add_link("UpdateSeconds", "out", "Update_ms_Calc", "inA")
    builder.add_link("Const_1000", "out", "Update_ms_Calc", "inB")

    # *** This is the critical link being tested. ***
    # It should trigger the special dual-link logic in the builder.
    print("Adding the dynamic link to the MultiVibrator's Period...")
    builder.add_link("Update_ms_Calc", "out", "TestMultiVibrator", "Period")

    # Wire the final output for visualization
    builder.add_link("TestMultiVibrator", "out", "PulseOutput", "in16")

    # --- Save the .bog file ---
    bog_filename = f"{script_filename}.bog"
    output_path = os.path.join(args.output_dir, bog_filename)
    os.makedirs(args.output_dir, exist_ok=True)
    builder.save(output_path)

    print(
        f"\nSuccessfully created Niagara .bog file at: {os.path.abspath(output_path)}"
    )
    print("Drag this file into Niagara Workbench to test the dynamic link.")


if __name__ == "__main__":
    main()
