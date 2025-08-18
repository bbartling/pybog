import sys
import os
import argparse

from bog_builder import BogFolderBuilder


def main():
    """
    This script uses the BogFolderBuilder to create a wiresheet that
    subtracts one number from another (Input_A - Input_B).
    """
    parser = argparse.ArgumentParser(
        description="Build a subtraction logic .bog file with automatic layout."
    )
    parser.add_argument(
        "-o", "--output_dir", default="examples", help="Output directory."
    )
    args = parser.parse_args()

    script_filename = os.path.basename(__file__).replace(".py", "")

    builder = BogFolderBuilder("SubtractionLogic")

    # --- Inputs ---
    builder.add_numeric_writable(name="Input_A", default_value=100.0)
    builder.add_numeric_writable(name="Input_B", default_value=40.0)

    # --- Output ---
    builder.add_numeric_writable(name="Difference")

    builder.start_sub_folder("CalculationLogic")
    builder.add_component(comp_type="kitControl:Subtract", name="Subtract")

    builder.end_sub_folder()

    builder.add_link("Input_A", "out", "Subtract", "inA")
    builder.add_link("Input_B", "out", "Subtract", "inB")
    builder.add_link("Subtract", "out", "Difference", "in16")

    bog_filename = f"{script_filename}.bog"
    output_path = os.path.join(args.output_dir, bog_filename)
    os.makedirs(args.output_dir, exist_ok=True)
    builder.save(output_path)
    print(f"\nSuccessfully created Niagara .bog file at: {output_path}")


if __name__ == "__main__":
    main()
