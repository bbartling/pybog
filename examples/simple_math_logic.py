import sys
import os
import argparse

# Add the 'src' directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.bog_builder import BogFolderBuilder


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

    # 1. Initialize the builder
    builder = BogFolderBuilder("ComplexMathEquation")

    # 2. Register all components for the equation.
    # The builder's layout engine will handle all positioning.

    # --- Inputs ---
    builder.add_numeric_writable(name="Input_A", default_value=20.0)
    builder.add_numeric_writable(name="Input_B", default_value=10.0)
    builder.add_numeric_writable(name="Input_C", default_value=2.0)
    builder.add_numeric_writable(name="Input_D", default_value=3.0)

    # --- Logic Blocks ---
    builder.add_component(comp_type="kitControl:Add", name="Add_AB")
    builder.add_component(comp_type="kitControl:Multiply", name="Multiply_ABC")
    builder.add_component(comp_type="kitControl:Divide", name="Divide_ABCD")

    # --- Output ---
    builder.add_numeric_writable(name="Result")

    # 3. Register all links to define the data flow.
    # This is the most critical part for the automatic layout engine.

    # First level of logic: (Input_A + Input_B)
    builder.add_link("Input_A", "out", "Add_AB", "inA")
    builder.add_link("Input_B", "out", "Add_AB", "inB")

    # Second level of logic: (Result of Add) * Input_C
    builder.add_link("Add_AB", "out", "Multiply_ABC", "inA")
    builder.add_link("Input_C", "out", "Multiply_ABC", "inB")

    # Third level of logic: (Result of Multiply) / Input_D
    builder.add_link("Multiply_ABC", "out", "Divide_ABCD", "inA")
    builder.add_link("Input_D", "out", "Divide_ABCD", "inB")

    # Final output link
    builder.add_link("Divide_ABCD", "out", "Result", "in16")

    # 4. Save the file.
    output_path = os.path.join(args.output_dir, "simple_math_logic_auto.bog")
    os.makedirs(args.output_dir, exist_ok=True)
    builder.save(output_path)
    print(f"Successfully created {output_path}")


if __name__ == "__main__":
    main()
