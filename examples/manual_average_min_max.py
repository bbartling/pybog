"""
Builds a comprehensive calculation engine that simultaneously finds the
average, minimum, and maximum values from a set of eleven numeric inputs.
The logic for each calculation (Avg, Min, Max) is organized into its own
dedicated sub-folder, demonstrating a clean and scalable layout for
complex, multi-part algorithms. This version uses tiered logic blocks
instead of a single component for each calculation.
"""

import sys
import os
import argparse

from bog_builder import BogFolderBuilder


def main():
    parser = argparse.ArgumentParser(
        description="Build a complex, multi-algorithm .bog file with a clean, multi-folder layout."
    )
    parser.add_argument(
        "-o", "--output_dir", default="examples", help="Output directory."
    )
    args = parser.parse_args()

    script_filename = os.path.basename(__file__).replace(".py", "")

    # 1. Initialize the builder
    builder = BogFolderBuilder("MultiAlgorithmTest")

    # --- Inputs ---
    builder.add_numeric_writable(name="Input1", default_value=10.0)
    builder.add_numeric_writable(name="Input2", default_value=20.0)
    builder.add_numeric_writable(name="Input3", default_value=30.0)
    builder.add_numeric_writable(name="Input4", default_value=40.0)
    builder.add_numeric_writable(name="Input5", default_value=50.0)
    builder.add_numeric_writable(name="Input6", default_value=60.0)
    builder.add_numeric_writable(name="Input7", default_value=70.0)
    builder.add_numeric_writable(name="Input8", default_value=80.0)
    builder.add_numeric_writable(name="Input9", default_value=90.0)
    builder.add_numeric_writable(name="Input10", default_value=100.0)
    builder.add_numeric_writable(name="Input11", default_value=110.0)

    # --- Outputs ---
    builder.add_numeric_writable(name="Min_Final")
    builder.add_numeric_writable(name="Max_Final")
    builder.add_numeric_writable(name="Avg_Final")

    builder.start_sub_folder("AverageLogic")
    builder.add_component(comp_type="kitControl:Average", name="Avg1")
    builder.add_component(comp_type="kitControl:Average", name="Avg2")
    builder.add_component(comp_type="kitControl:Average", name="Avg3")
    builder.add_component(comp_type="kitControl:Average", name="Avg4")
    builder.end_sub_folder()

    builder.start_sub_folder("MinimumLogic")
    builder.add_component(comp_type="kitControl:Minimum", name="Min1")
    builder.add_component(comp_type="kitControl:Minimum", name="Min2")
    builder.add_component(comp_type="kitControl:Minimum", name="Min3")
    builder.add_component(comp_type="kitControl:Minimum", name="Min4")
    builder.end_sub_folder()

    builder.start_sub_folder("MaximumLogic")
    builder.add_component(comp_type="kitControl:Maximum", name="Max1")
    builder.add_component(comp_type="kitControl:Maximum", name="Max2")
    builder.add_component(comp_type="kitControl:Maximum", name="Max3")
    builder.add_component(comp_type="kitControl:Maximum", name="Max4")
    builder.end_sub_folder()

    # --- Links for Average Logic ---
    builder.add_link("Input1", "out", "Avg1", "inA")
    builder.add_link("Input2", "out", "Avg1", "inB")
    builder.add_link("Input3", "out", "Avg1", "inC")
    builder.add_link("Input4", "out", "Avg1", "inD")
    builder.add_link("Input5", "out", "Avg2", "inA")
    builder.add_link("Input6", "out", "Avg2", "inB")
    builder.add_link("Input7", "out", "Avg2", "inC")
    builder.add_link("Input8", "out", "Avg2", "inD")
    builder.add_link("Input9", "out", "Avg3", "inA")
    builder.add_link("Input10", "out", "Avg3", "inB")
    builder.add_link("Input11", "out", "Avg3", "inC")
    builder.add_link("Avg1", "out", "Avg4", "inA")
    builder.add_link("Avg2", "out", "Avg4", "inB")
    builder.add_link("Avg3", "out", "Avg4", "inC")
    builder.add_link("Avg4", "out", "Avg_Final", "in16")

    # --- Links for Minimum Logic ---
    builder.add_link("Input1", "out", "Min1", "inA")
    builder.add_link("Input2", "out", "Min1", "inB")
    builder.add_link("Input3", "out", "Min1", "inC")
    builder.add_link("Input4", "out", "Min1", "inD")
    builder.add_link("Input5", "out", "Min2", "inA")
    builder.add_link("Input6", "out", "Min2", "inB")
    builder.add_link("Input7", "out", "Min2", "inC")
    builder.add_link("Input8", "out", "Min2", "inD")
    builder.add_link("Input9", "out", "Min3", "inA")
    builder.add_link("Input10", "out", "Min3", "inB")
    builder.add_link("Input11", "out", "Min3", "inC")
    builder.add_link("Min1", "out", "Min4", "inA")
    builder.add_link("Min2", "out", "Min4", "inB")
    builder.add_link("Min3", "out", "Min4", "inC")
    builder.add_link("Min4", "out", "Min_Final", "in16")

    # --- Links for Maximum Logic ---
    builder.add_link("Input1", "out", "Max1", "inA")
    builder.add_link("Input2", "out", "Max1", "inB")
    builder.add_link("Input3", "out", "Max1", "inC")
    builder.add_link("Input4", "out", "Max1", "inD")
    builder.add_link("Input5", "out", "Max2", "inA")
    builder.add_link("Input6", "out", "Max2", "inB")
    builder.add_link("Input7", "out", "Max2", "inC")
    builder.add_link("Input8", "out", "Max2", "inD")
    builder.add_link("Input9", "out", "Max3", "inA")
    builder.add_link("Input10", "out", "Max3", "inB")
    builder.add_link("Input11", "out", "Max3", "inC")
    builder.add_link("Max1", "out", "Max4", "inA")
    builder.add_link("Max2", "out", "Max4", "inB")
    builder.add_link("Max3", "out", "Max4", "inC")
    builder.add_link("Max4", "out", "Max_Final", "in16")

    bog_filename = f"{script_filename}.bog"
    output_path = os.path.join(args.output_dir, bog_filename)
    os.makedirs(args.output_dir, exist_ok=True)
    builder.save(output_path)
    print(f"\nSuccessfully created Niagara .bog file at: {output_path}")


if __name__ == "__main__":
    main()
