"""Example script for generating a PID loop .bog file.

This example uses a `kitControl:LoopPoint` block to implement a basic PID
controller.  The loop point accepts a process variable (e.g. temperature), a
setpoint, a boolean enable, a loop action (an enum derived from a boolean
status), and tuning constants for the proportional and integral terms.  The
script demonstrates how to wire numeric and boolean writables to these slots
and how to use explicit conversion links when a type conversion is required.

Note that the example would be for a cooling valve where if a reverse
acting PID was needed for a heating valve LoopActionDirect would need
to be set True.

"""

from __future__ import annotations

import argparse
import os
import sys


from bog_builder import BogFolderBuilder


def build_pid_loop(output_directory: str) -> str:

    builder = BogFolderBuilder("PID", debug=True)

    # Define process variable and setpoint numeric writables
    builder.add_numeric_writable("Temp", default_value=80.0)
    builder.add_numeric_writable("Setpoint", default_value=70.0)
    # Define tuning writables
    builder.add_numeric_writable("PropBand", default_value=5.0)
    builder.add_numeric_writable("Integral", default_value=0.05)
    # Define boolean writables for enabling and loop action
    builder.add_boolean_writable("BooleanWritable", default_value=True)
    builder.add_boolean_writable("LoopActionDirect", default_value=False)

    # Create the LoopPoint with fallback values matching our writables
    lp_props = {
        "loopEnable": {"value": True},
        "controlledVariable": {"value": 80.0},
        "setpoint": {"value": 70.0},
        "proportionalConstant": {"value": 5.0},
        "integralConstant": {"value": 0.05},
    }
    # Use the dedicated wrapper for the LoopPoint component
    builder.add_loop_point("LoopPoint", properties=lp_props)

    # Define an output writable for the PID result
    builder.add_numeric_writable("Output")

    # Wire the process variable and setpoint directly
    builder.add_link("Temp", "out", "LoopPoint", "controlledVariable")
    builder.add_link("Setpoint", "out", "LoopPoint", "setpoint")

    # Conversion from a boolean writable to the loopAction enum
    builder.add_link(
        "LoopActionDirect",
        "out",
        "LoopPoint",
        "loopAction",
        link_type="b:ConversionLink",
        converter_type="conv:StatusBooleanToFrozenEnum",
    )

    # Link the enable boolean directly
    builder.add_link("BooleanWritable", "out", "LoopPoint", "loopEnable")

    # Conversion from numeric writables to numbers for the tuning constants
    builder.add_link(
        "PropBand",
        "out",
        "LoopPoint",
        "proportionalConstant",
        link_type="b:ConversionLink",
        converter_type="conv:StatusNumericToNumber",
    )
    builder.add_link(
        "Integral",
        "out",
        "LoopPoint",
        "integralConstant",
        link_type="b:ConversionLink",
        converter_type="conv:StatusNumericToNumber",
    )

    # Connect the LoopPoint output to the output writable
    builder.add_link("LoopPoint", "out", "Output", "in10")

    # Write the .bog file
    os.makedirs(output_directory, exist_ok=True)
    out_path = os.path.join(output_directory, "PID.bog")
    builder.save(out_path)
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a PID loop .bog file.")
    parser.add_argument(
        "-o",
        "--output",
        default="examples",
        help="Directory to write the output .bog file (defaults to 'examples').",
    )
    args = parser.parse_args()
    out_dir = args.output
    path = build_pid_loop(out_dir)
    print(f"Created {path}")


if __name__ == "__main__":
    main()
