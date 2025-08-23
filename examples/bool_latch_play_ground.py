"""
A testing environment or "playground" for a BooleanLatch component. This
script generates a fluctuating SineWave as a simulated process variable.
The SineWave's value is compared against high and low thresholds (TOP and BOTTOM)
to generate 'set' and 'reset' (or clock) signals for the latch. This is a common
pattern for creating stateful alarms or mode changes based on an analog value.
"""

import sys
import os
import argparse

from bog_builder import BogFolderBuilder


def main():
    parser = argparse.ArgumentParser(
        description="Build a .bog: SineWave → thresholds → OR → BooleanLatch playground."
    )
    parser.add_argument(
        "-o",
        "--output_dir",
        default="examples",
        help="Output directory for the .bog file.",
    )
    args = parser.parse_args()

    script_filename = os.path.basename(__file__).replace(".py", "")
    builder = BogFolderBuilder("BoolLatch_Playground", debug=True)

    # -------- Top-level user knobs / display --------
    builder.add_numeric_writable("TOP", default_value=90.0, precision=2)
    builder.add_numeric_writable("BOTTOM", default_value=10.0, precision=2)
    builder.add_boolean_writable("CountDown", default_value=False)  # display latch OUT
    builder.add_component("kitControl:SineWave", "SineWave")

    # -------- Logic folder --------
    builder.start_sub_folder("LatchSandbox")

    builder.add_component("kitControl:GreaterThanEqual", "GreaterThanEq")
    builder.add_component("kitControl:LessThanEqual", "LessThanEq")
    builder.add_component("kitControl:Or", "Or_Block")
    builder.add_component("kitControl:BooleanLatch", "BooleanLatch")

    builder.end_sub_folder()

    # -------- Wiring (match GOOD.xml exactly) --------
    # Sine wave to both comparators (inA)
    builder.add_link("SineWave", "out", "GreaterThanEq", "inA")
    builder.add_link("SineWave", "out", "LessThanEq", "inA")

    # Thresholds to comparators (inB)
    builder.add_link("TOP", "out", "GreaterThanEq", "inB")
    builder.add_link("BOTTOM", "out", "LessThanEq", "inB")

    # Comparator outputs into OR
    builder.add_link("GreaterThanEq", "out", "Or_Block", "inA")
    builder.add_link("LessThanEq", "out", "Or_Block", "inB")

    # this is the latch reset to the clock input
    builder.add_link("GreaterThanEq", "out", "BooleanLatch", "clock")

    builder.add_link("Or_Block", "out", "BooleanLatch", "in")

    # Expose the latched OUT at top-level display point
    builder.add_link("BooleanLatch", "out", "CountDown", "in16")

    # -------- Save .bog --------
    os.makedirs(args.output_dir, exist_ok=True)
    out_path = os.path.join(args.output_dir, f"{script_filename}.bog")
    builder.save(out_path)
    print(f"Created Niagara .bog at: {out_path}")


if __name__ == "__main__":
    main()
