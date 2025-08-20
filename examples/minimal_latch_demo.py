"""
A minimal demonstration for testing the core functionality of a
`kitControl:BooleanLatch`. This script provides direct, manual boolean
writables for the 'in' and 'clock' signals of the latch, allowing a user
to step through the latching process to understand its behavior in isolation.
"""

import sys
import os
import argparse

from bog_builder import BogFolderBuilder


def main():
    """
    Builds a minimal .bog file to test the wiring of a kitControl:BooleanLatch.
    """
    parser = argparse.ArgumentParser(
        description="Build a minimal .bog file to test the BooleanLatch component."
    )
    parser.add_argument(
        "-o",
        "--output_dir",
        default="examples",
        help="Output directory for the .bog file.",
    )
    args = parser.parse_args()

    script_filename = os.path.basename(__file__).replace(".py", "")
    builder = BogFolderBuilder("Minimal_Latch_Demo", debug=True)

    # -------- Component Creation --------
    # A controllable switch for the main input signal.
    builder.add_boolean_writable("Input_Signal", default_value=False)

    # A controllable switch to trigger the latch's clock.
    builder.add_boolean_writable("Clock_Signal", default_value=False)

    # The BooleanLatch component under test.
    builder.add_component("kitControl:BooleanLatch", "My_Latch")

    # A point to display the final latched value.
    builder.add_boolean_writable("Latched_Output", default_value=False)

    builder.add_link("Input_Signal", "out", "My_Latch", "in")
    builder.add_link("Clock_Signal", "out", "My_Latch", "clock")

    # Link the latch's output to the display component's input ('in16' for BooleanWritable).
    builder.add_link("My_Latch", "out", "Latched_Output", "in16")

    # -------- Save .bog --------
    os.makedirs(args.output_dir, exist_ok=True)
    out_path = os.path.join(args.output_dir, f"{script_filename}.bog")
    builder.save(out_path)
    print(f"Created Niagara .bog at: {out_path}")


if __name__ == "__main__":
    main()
