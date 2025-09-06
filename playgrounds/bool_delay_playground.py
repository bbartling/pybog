"""
Boolean Delay Playground (seconds-based, adjustable)
----------------------------------------------------

This playground creates a BooleanDelay component with its delay times wired to
numeric writeables so you can adjust them interactively in Workbench.

- Bool_Input (BooleanWritable)
- OnDelay_Sec (NumericWritable, seconds)
- OffDelay_Sec (NumericWritable, seconds)
- Bool_Output (BooleanWritable result)

The numeric writeables drive the onDelay/offDelay inputs dynamically.
"""

import os
import argparse
from bog_builder import BogFolderBuilder


def main():
    parser = argparse.ArgumentParser(
        description="BooleanDelay playground with adjustable delays."
    )
    parser.add_argument(
        "-o",
        "--output_dir",
        default="examples",
        help="Output directory for the .bog file.",
    )
    args = parser.parse_args()

    script_filename = os.path.basename(__file__).replace(".py", "")
    builder = BogFolderBuilder("BoolDelay_Playground", debug=True)

    # --- Inputs / Outputs ---
    builder.add_boolean_writable("Bool_Input", default_value=False)
    builder.add_boolean_writable("Bool_Output")

    # Numeric writeables to set delays (seconds).
    builder.add_numeric_writable("OnDelay_Sec", default_value=5.0)
    builder.add_numeric_writable("OffDelay_Sec", default_value=10.0)

    # --- Delay block ---
    # No fixed properties, inputs will be wired.
    builder.add_component("kitControl:BooleanDelay", "BoolDelay")

    # --- Wiring ---
    builder.add_link("Bool_Input", "out", "BoolDelay", "in")
    builder.add_link("OnDelay_Sec", "out", "BoolDelay", "onDelay")
    builder.add_link("OffDelay_Sec", "out", "BoolDelay", "offDelay")
    builder.add_link("BoolDelay", "out", "Bool_Output", "in16")

    # --- Save ---
    os.makedirs(args.output_dir, exist_ok=True)
    out_path = os.path.join(args.output_dir, f"{script_filename}.bog")
    builder.save(out_path)
    print(f"Created Niagara .bog at: {out_path}")


if __name__ == "__main__":
    main()
