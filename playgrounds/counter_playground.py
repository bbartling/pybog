"""
A simple "playground" for demonstrating and testing the kitControl:Counter
component. This script creates a single counter with manual controls for
incrementing, clearing, and setting the increment value.

This example addresses a common issue where the counter's output needs to be
displayed in a NumericWritable with specific units, such as seconds. It
demonstrates the correct way to specify units as a facet when creating
the writable point.

Algorithm:
- Manual_Pulse (BooleanWritable): Triggers the 'countUp' slot.
- Manual_Clear (BooleanWritable): Triggers the 'clear' slot.
- Increment_Value (NumericWritable): Sets the 'countIncrement' value.
- Counter_Output (NumericWritable): Displays the counter's 'out' value,
  configured with units of 'seconds' and a precision of 0.
"""

import os
import sys
import argparse

# Per instructions, append to sys.path to find bog_builder
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))
from bog_builder import BogFolderBuilder


def main():
    """
    Main function to build and save the counter playground .bog file.
    """
    parser = argparse.ArgumentParser(
        description="Build a .bog file to demonstrate the kitControl:Counter component."
    )
    parser.add_argument(
        "-o",
        "--output_dir",
        default="examples",
        help="Output directory for the .bog file.",
    )
    args = parser.parse_args()

    builder = BogFolderBuilder("CounterPlayground", debug=True)

    print("--- Creating Top-Level I/O Components ---")

    # --- Inputs for controlling the counter ---
    builder.add_boolean_writable("Manual_Pulse", default_value=False)
    builder.add_boolean_writable("Manual_Clear", default_value=False)
    builder.add_numeric_writable("Increment_Value", default_value=1.0)
    builder.add_numeric_writable("Counter_Output", precision=0)

    # --- Logic Component ---
    builder.add_counter("Test_Counter")

    print("\n--- Wiring Components ---")

    # Wire the manual controls to the counter's slots
    builder.add_link("Manual_Pulse", "out", "Test_Counter", "countUp")
    builder.add_link("Manual_Clear", "out", "Test_Counter", "clear")
    builder.add_link("Increment_Value", "out", "Test_Counter", "countIncrement")

    # Wire the counter's numeric output to the display writable
    builder.add_link("Test_Counter", "out", "Counter_Output", "in16")

    # --- Save the .bog file ---
    # Per instructions, hardcode the output filename.
    bog_filename = "counter_playground.bog"
    output_path = os.path.join(args.output_dir, bog_filename)
    os.makedirs(args.output_dir, exist_ok=True)
    builder.save(output_path)

    print(
        f"\nSuccessfully created Niagara .bog file at: {os.path.abspath(output_path)}"
    )
    print("Drag this file into Niagara Workbench to test the counter.")


if __name__ == "__main__":
    main()
