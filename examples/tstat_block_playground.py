"""
kitControl:Tstat Heating Playground
------------------------------------

This script creates a simple demonstration of the kitControl:Tstat component,
configured for a common HVAC heating enable scenario.

This is a VERY common block human controls techs like to use to
enable equipment to run based on outdoor air temp compare to stp as
it has a nice differential feature built inside. Use this block Vs
hard coding comparaters and making your own hysteresis algorithm as the
humans may not accept that code base purely because you didnt use the
Tstat block which they are used to seeing.

Algorithm:
- An Outside Air Temperature (OAT) is used as the controlled variable (cv).
- When the OAT drops below the HeatEnableSp (sp), the Tstat block's output
  will turn on, enabling the heating system.
- A fixed differential (diff) of 2.0 degrees provides a deadband to prevent
  short-cycling.
- The 'action' is set to reverse (True), which is typical for heating logic
  (i.e., the output turns on as the input value falls).

This serves as a clear, interactive example of the Tstat block's functionality.
"""

import os
import argparse
from bog_builder import BogFolderBuilder


def main():
    """
    Main function to build and save the Tstat playground .bog file.
    """
    parser = argparse.ArgumentParser(
        description="Build a .bog file to demonstrate the kitControl:Tstat component for heating."
    )
    parser.add_argument(
        "-o",
        "--output_dir",
        default="examples",
        help="Output directory for the .bog file.",
    )
    args = parser.parse_args()

    script_filename = os.path.basename(__file__).replace(".py", "")
    builder = BogFolderBuilder("TstatHeatingPlayground", debug=True)

    print("--- Creating Components for Tstat Playground ---")

    # --- Inputs (User-adjustable points) ---
    builder.add_numeric_writable("OAT", default_value=55.0, precision=1)
    builder.add_numeric_writable("HeatEnableSp", default_value=50.0, precision=1)

    # --- Configuration (Fixed constants) ---
    builder.add_component(
        "kitControl:NumericConst", "Differential", properties={"value": 2.0}
    )
    # Action=True corresponds to 'Reverse' for heating logic
    builder.add_component(
        "kitControl:BooleanConst", "Action_Reverse", properties={"value": True}
    )
    builder.add_component(
        "kitControl:BooleanConst", "NullOnInControl_False", properties={"value": False}
    )

    # --- Core Logic Block ---
    builder.add_component("kitControl:Tstat", "Tstat")

    # --- Output ---
    builder.add_boolean_writable("HeatCommand")

    print("\n--- Wiring Components ---")

    # Wire the main inputs to the Tstat block
    builder.add_link("OAT", "out", "Tstat", "cv")
    builder.add_link("HeatEnableSp", "out", "Tstat", "sp")
    builder.add_link("Differential", "out", "Tstat", "diff")

    # Wire the configuration constants
    builder.add_link("Action_Reverse", "out", "Tstat", "action")
    builder.add_link("NullOnInControl_False", "out", "Tstat", "nullOnInactive")

    # Wire the final command to the output writable for viewing
    builder.add_link("Tstat", "out", "HeatCommand", "in16")

    # --- Save the .bog file ---
    bog_filename = f"{script_filename}.bog"
    output_path = os.path.join(args.output_dir, bog_filename)
    os.makedirs(args.output_dir, exist_ok=True)
    builder.save(output_path)

    print(
        f"\nSuccessfully created Niagara .bog file at: {os.path.abspath(output_path)}"
    )
    print("Drag this file into Niagara Workbench to test the Tstat logic.")


if __name__ == "__main__":
    main()
