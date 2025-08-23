"""
A straightforward example of summing four numeric inputs. This script uses
a single `kitControl:Add` block, which can accept up to four inputs directly
(inA, inB, inC, inD). It demonstrates the most direct way to perform a simple
multi-input addition.
"""

import sys
import os
import argparse

from bog_builder import BogFolderBuilder


def main():
    parser = argparse.ArgumentParser(
        description="Build a 4-input adder .bog"
    )
    parser.add_argument(
        "-o", "--output_dir", default="examples", help="Output directory."
    )
    args = parser.parse_args()

    script_filename = os.path.basename(__file__).replace(".py", "")

    builder = BogFolderBuilder("AutoLayoutFourInputAdder")

    # --- Inputs ---
    builder.add_numeric_writable(name="Input1", default_value=10.0)
    builder.add_numeric_writable(name="Input2", default_value=20.0)
    builder.add_numeric_writable(name="Input3", default_value=30.0)
    builder.add_numeric_writable(name="Input4", default_value=40.0)

    # --- Output ---
    builder.add_numeric_writable(name="Sum")

    builder.add_component(comp_type="kitControl:Add", name="Add")

    builder.add_link("Input1", "out", "Add", "inA")
    builder.add_link("Input2", "out", "Add", "inB")
    builder.add_link("Input3", "out", "Add", "inC")
    builder.add_link("Input4", "out", "Add", "inD")
    builder.add_link("Add", "out", "Sum", "in16")

    bog_filename = f"{script_filename}.bog"
    output_path = os.path.join(args.output_dir, bog_filename)
    os.makedirs(args.output_dir, exist_ok=True)
    builder.save(output_path)
    print(f"\nSuccessfully created Niagara .bog file at: {output_path}")


if __name__ == "__main__":
    main()
