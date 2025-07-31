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

    # 1. Initialize the builder
    builder = BogFolderBuilder("ComplexMathEquation")

    # 2. Register all TOP-LEVEL components.
    # These are the clean inputs and outputs the user will interact with.
    # They are created before we enter the sub-folder "sandbox".

    # --- Inputs ---
    builder.add_numeric_writable(name="Input_A", default_value=20.0)
    builder.add_numeric_writable(name="Input_B", default_value=10.0)
    builder.add_numeric_writable(name="Input_C", default_value=2.0)
    builder.add_numeric_writable(name="Input_D", default_value=3.0)

    # --- Output ---
    builder.add_numeric_writable(name="Result")


    # TUTORIAL: HOW TO USE SUB-FOLDERS
    # The concept is simple: we create a "sandbox" for our complex logic.
    # Anything created inside this sandbox will be placed in a sub-folder.

    # STEP 1: Start the sub-folder.
    # We give it a descriptive name. This name will appear on the folder
    # icon in the top-level wiresheet.
    # To see the logic flat for debugging, you can simply comment out this line.
    builder.start_sub_folder("CalculationLogic")

    # --- Logic Blocks ---
    # Because the following add_component calls are inside the "sandbox",
    # the builder will automatically place them inside the "CalculationLogic" folder.
    builder.add_component(comp_type="kitControl:Add", name="Add_AB")
    builder.add_component(comp_type="kitControl:Multiply", name="Multiply_ABC")
    builder.add_component(comp_type="kitControl:Divide", name="Divide_ABCD")

    # STEP 2: End the sub-folder.
    # This closes the "sandbox". Any components added after this line will
    # be back at the top level.
    # To see the logic flat for debugging, you can simply comment out this line.
    builder.end_sub_folder()


    # 3. Register all links to define the data flow.
    # You DO NOT need to change this section at all. The BogFolderBuilder is
    # smart enough to see that a link like "Input_A" -> "Add_AB" is crossing
    # a folder boundary. It will automatically create the necessary ProxyIn
    # and ProxyOut points to make the connection work.

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
    bog_filename = f"{script_filename}.bog"
    output_path = os.path.join(args.output_dir, bog_filename)
    os.makedirs(args.output_dir, exist_ok=True)
    builder.save(output_path)
    print(f"\nSuccessfully created Niagara .bog file at: {output_path}")


if __name__ == "__main__":
    main()
