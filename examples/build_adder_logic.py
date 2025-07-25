# examples/build_adder_logic.py
import sys
import os
import argparse

# Add the 'src' directory to the Python path so we can import the builder
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.bog_builder import BogFolderBuilder

def main():
    """
    This script demonstrates how to use the BogFolderBuilder to programmatically
    create a Niagara wiresheet with simple adder logic.
    It accepts a command-line argument to specify the output directory.
    """
    # Set up the command-line argument parser
    parser = argparse.ArgumentParser(
        description="Build a Niagara .bog file for a simple adder logic.",
        epilog="Example:\n"
               "  python examples/build_adder_logic.py -o \"C:\\path\\to\\your\\output\\directory\""
    )
    parser.add_argument(
        "-o", "--output_dir",
        default="examples",
        help="The directory where the .bog file will be saved. Defaults to the 'examples' directory."
    )
    args = parser.parse_args()

    # 1. Initialize the builder with a name for the main folder
    builder = BogFolderBuilder("MyAdderLogic")

    # 2. Add the components, specifying their type, name, and properties.
    # The following coordinates adhere to the Hierarchical Data Flow layout
    # strategy, arranging blocks in a clean left-to-right grid.

    # Input 1: A settable numeric point with a default value of 6.0
    builder.add_numeric_writable(
        name="Input1",
        default_value=6.0,
        ws_annotation="10,10,8" # x, y, size
    )

    # Input 2: A settable numeric point with a default value of 4.0
    builder.add_numeric_writable(
        name="Input2",
        default_value=4.0,
        ws_annotation="10,20,8" # Positioned vertically below Input1
    )

    # Add block: The core logic component from the kitControl palette
    builder.add_component(
        comp_type="kitControl:Add",
        name="Add",
        ws_annotation="20,15,8" # Positioned to the right, centered between inputs
    )

    # Sum: A read-only numeric point to display the result
    builder.add_numeric_writable(
        name="Sum",
        read_only=True,
        ws_annotation="30,15,8" # Positioned in the next column to the right
    )

    # 3. Add the links between the components to define the data flow.
    # The builder uses the component names to find the correct handles.
    builder.add_link(
        source_comp_name="Input1", source_slot="out",
        target_comp_name="Add", target_slot="inA"
    )
    builder.add_link(
        source_comp_name="Input2", source_slot="out",
        target_comp_name="Add", target_slot="inB"
    )
    builder.add_link(
        source_comp_name="Add", source_slot="out",
        target_comp_name="Sum", target_slot="in16" # 'in16' is the standard input for writable points
    )

    # 4. Save the final result to a .bog file in the specified directory
    file_name = "adder_logic.bog"
    output_path = os.path.join(args.output_dir, file_name)
    
    # Ensure the output directory exists
    os.makedirs(args.output_dir, exist_ok=True)
    
    builder.save(output_path)

if __name__ == "__main__":
    main()
