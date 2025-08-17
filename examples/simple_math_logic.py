import sys
import os
import argparse

# Add the 'src' directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
# Make sure you are importing the new builder with sub-folder capabilities
from src.bog_builder_new import BogFolderBuilder


def main():
    """
    This script tests the BogFolderBuilder with a more complex algorithm
    that combines multiple math blocks to calculate:
    Result = ((Input_A + Input_B) * Input_C) / Input_D
    """
    parser = argparse.ArgumentParser(
        description="Build a complex math logic .bog file with automatic layout."
    )
    parser.add_argument(
        "-o", "--output_dir", default="examples", help="Output directory."
    )
    args = parser.parse_args()

    script_filename = os.path.basename(__file__).replace(".py", "")

    builder = BogFolderBuilder("ComplexMathEquation")

    builder.start_sub_folder("CalculationLogic")
    
    # --- Inputs ---
    builder.add_numeric_writable(name="Input_A", default_value=20.0)
    builder.add_numeric_writable(name="Input_B", default_value=10.0)
    builder.add_numeric_writable(name="Input_C", default_value=2.0)
    builder.add_numeric_writable(name="Input_D", default_value=3.0)

    # --- Output ---
    builder.add_numeric_writable(name="Result")

    builder.add_component(comp_type="kitControl:Add", name="Add_AB")
    builder.add_component(comp_type="kitControl:Multiply", name="Multiply_ABC")
    builder.add_component(comp_type="kitControl:Divide", name="Divide_ABCD")

    builder.end_sub_folder()

    builder.add_link("Input_A", "out", "Add_AB", "inA")
    builder.add_link("Input_B", "out", "Add_AB", "inB")

    builder.add_link("Add_AB", "out", "Multiply_ABC", "inA")
    builder.add_link("Input_C", "out", "Multiply_ABC", "inB")

    builder.add_link("Multiply_ABC", "out", "Divide_ABCD", "inA")
    builder.add_link("Input_D", "out", "Divide_ABCD", "inB")

    builder.add_link("Divide_ABCD", "out", "Result", "in16")

    bog_filename = f"{script_filename}.bog"
    output_path = os.path.join(args.output_dir, bog_filename)
    os.makedirs(args.output_dir, exist_ok=True)
    builder.save(output_path)
    print(f"\nSuccessfully created Niagara .bog file at: {output_path}")


if __name__ == "__main__":
    main()