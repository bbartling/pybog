"""
numeric_delay_playground.py

This script builds a simple "playground" or test environment for the
kitControl:NumericDelay component, matching a direct-wired layout. It allows
a user to observe how the component continuously delays a changing input value.

Algorithm Overview:
-------------------
1.  **Inputs:** A numeric value to delay, a delay time in minutes (defaulting
    to 1), and a max step size are provided as user-configurable writables.
2.  **Delay Time Conversion:** The 'DelayTimeMinutes' is converted to
    milliseconds to correctly configure the 'updateTime' property of the
    NumericDelay block.
3.  **Delay Logic:** The NumericDelay component is directly linked to the
    'ValueToDelay' input. It continuously attempts to match its output to the
    input value, but its rate of change is limited by the 'updateTime' and
    'maxStepSize', effectively slewing the value over time.
"""

import sys
import os
import argparse

from bog_builder import BogFolderBuilder


def main():
    parser = argparse.ArgumentParser(
        description="Build a .bog file for a NumericDelay playground."
    )
    parser.add_argument(
        "-o",
        "--output_dir",
        default="examples",
        help="Output directory for the .bog file.",
    )
    args = parser.parse_args()

    script_filename = os.path.basename(__file__).replace(".py", "")
    builder = BogFolderBuilder("NumericDelayPlayground", debug=True)

    # --- Top-level I/O and Configuration ---
    builder.add_numeric_writable("ValueToDelay", default_value=100.0, precision=2)
    builder.add_numeric_writable("DelayTimeMinutes", default_value=1.0, precision=2)
    builder.add_numeric_writable("MaxStepSize", default_value=0.5, precision=2)
    builder.add_numeric_writable("DelayedOutput", default_value=0.0, precision=2)

    # --- Logic Components (No Sub-folder) ---
    # The core NumericDelay component
    builder.add_component("kitControl:NumericDelay", "MainDelay")

    # Logic to convert minutes to milliseconds for the delay time
    builder.add_component(
        "kitControl:NumericConst", "Const_60000", properties={"value": 60000.0}
    )
    builder.add_component("kitControl:Multiply", "Delay_ms_Calc")

    # --- Wiring ---

    # Wire the value and configuration directly to the NumericDelay block
    builder.add_link("ValueToDelay", "out", "MainDelay", "in")
    builder.add_link("MaxStepSize", "out", "MainDelay", "maxStepSize")

    # Wire the delay time calculation
    builder.add_link("DelayTimeMinutes", "out", "Delay_ms_Calc", "inA")
    builder.add_link("Const_60000", "out", "Delay_ms_Calc", "inB")
    builder.add_link(
        "Delay_ms_Calc",
        "out",
        "MainDelay",
        "updateTime",
        link_type="b:ConversionLink",
        converter_type="conv:StatusNumericToRelTime",
    )

    # Wire the final delayed value to the output
    builder.add_link("MainDelay", "out", "DelayedOutput", "in16")

    # --- Save the .bog file ---
    os.makedirs(args.output_dir, exist_ok=True)
    out = os.path.join(args.output_dir, f"{script_filename}.bog")
    builder.save(out)
    print(f"Successfully created Niagara .bog file at: {os.path.abspath(out)}")


if __name__ == "__main__":
    main()
