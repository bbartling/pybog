import sys
import os
import argparse

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.bog_builder import BogFolderBuilder


def main():
    parser = argparse.ArgumentParser(
        description="Boolean Logic Playground for Niagara logic blocks."
    )
    parser.add_argument(
        "-o", "--output_dir", default="examples", help="Output directory."
    )
    args = parser.parse_args()

    builder = BogFolderBuilder("BoolLogic_Playground", debug=True)

    # === Inputs ===
    builder.add_boolean_writable("Bool_A", default_value=True)
    builder.add_boolean_writable("Bool_B", default_value=False)
    builder.add_numeric_writable("Num_A", default_value=5.0)
    builder.add_numeric_writable("Num_B", default_value=10.0)

    # === Boolean Logic Blocks ===
    builder.add_component("kitControl:And", "And_Block")
    builder.add_component("kitControl:Or", "Or_Block")
    builder.add_component("kitControl:Xor", "Xor_Block")
    builder.add_component("kitControl:Not", "Not_Block")

    # === Comparison Blocks ===
    builder.add_component("kitControl:Equal", "Equal_Block")
    builder.add_component("kitControl:NotEqual", "NotEqual_Block")
    builder.add_component("kitControl:GreaterThan", "GreaterThan_Block")
    builder.add_component("kitControl:GreaterThanEqual", "GreaterThanEqual_Block")
    builder.add_component("kitControl:LessThan", "LessThan_Block")
    builder.add_component("kitControl:LessThanEqual", "LessThanEqual_Block")

    # === Outputs ===
    builder.add_boolean_writable("Bool_Output_And")
    builder.add_boolean_writable("Bool_Output_Or")
    builder.add_boolean_writable("Bool_Output_Xor")
    builder.add_boolean_writable("Bool_Output_Not")
    builder.add_boolean_writable("Bool_Output_Equal")
    builder.add_boolean_writable("Bool_Output_NotEqual")
    builder.add_boolean_writable("Bool_Output_GT")
    builder.add_boolean_writable("Bool_Output_GTE")
    builder.add_boolean_writable("Bool_Output_LT")
    builder.add_boolean_writable("Bool_Output_LTE")

    # === Wiring ===
    # Boolean Logic: A and B
    builder.add_link("Bool_A", "out", "And_Block", "inA")
    builder.add_link("Bool_B", "out", "And_Block", "inB")
    builder.add_link("And_Block", "out", "Bool_Output_And", "in16")

    builder.add_link("Bool_A", "out", "Or_Block", "inA")
    builder.add_link("Bool_B", "out", "Or_Block", "inB")
    builder.add_link("Or_Block", "out", "Bool_Output_Or", "in16")

    builder.add_link("Bool_A", "out", "Xor_Block", "inA")
    builder.add_link("Bool_B", "out", "Xor_Block", "inB")
    builder.add_link("Xor_Block", "out", "Bool_Output_Xor", "in16")

    builder.add_link("Bool_B", "out", "Not_Block", "in")
    builder.add_link("Not_Block", "out", "Bool_Output_Not", "in16")

    # Comparisons: Num_A vs Num_B
    builder.add_link("Num_A", "out", "Equal_Block", "inA")
    builder.add_link("Num_B", "out", "Equal_Block", "inB")
    builder.add_link("Equal_Block", "out", "Bool_Output_Equal", "in16")

    builder.add_link("Num_A", "out", "NotEqual_Block", "inA")
    builder.add_link("Num_B", "out", "NotEqual_Block", "inB")
    builder.add_link("NotEqual_Block", "out", "Bool_Output_NotEqual", "in16")

    builder.add_link("Num_A", "out", "GreaterThan_Block", "inA")
    builder.add_link("Num_B", "out", "GreaterThan_Block", "inB")
    builder.add_link("GreaterThan_Block", "out", "Bool_Output_GT", "in16")

    builder.add_link("Num_A", "out", "GreaterThanEqual_Block", "inA")
    builder.add_link("Num_B", "out", "GreaterThanEqual_Block", "inB")
    builder.add_link("GreaterThanEqual_Block", "out", "Bool_Output_GTE", "in16")

    builder.add_link("Num_A", "out", "LessThan_Block", "inA")
    builder.add_link("Num_B", "out", "LessThan_Block", "inB")
    builder.add_link("LessThan_Block", "out", "Bool_Output_LT", "in16")

    builder.add_link("Num_A", "out", "LessThanEqual_Block", "inA")
    builder.add_link("Num_B", "out", "LessThanEqual_Block", "inB")
    builder.add_link("LessThanEqual_Block", "out", "Bool_Output_LTE", "in16")

    # === Save file ===
    output_path = os.path.join(args.output_dir, "bool_logic_playground.bog")
    os.makedirs(args.output_dir, exist_ok=True)
    builder.save(output_path)
    print(f"Successfully created {output_path}")


if __name__ == "__main__":
    main()
