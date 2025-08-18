import sys
import os
import argparse

from bog_builder import BogFolderBuilder


def create_comparison_node(builder, input_a_name, input_b_name, node_id):
    """
    Creates a set of blocks to find the max and min of two inputs.
    """
    gt_name = f"GT_{node_id}"
    max_switch_name = f"MaxSwitch_{node_id}"
    min_switch_name = f"MinSwitch_{node_id}"

    # Add the necessary logic blocks
    builder.add_component("kitControl:GreaterThan", gt_name)
    builder.add_numeric_switch(max_switch_name)
    builder.add_numeric_switch(min_switch_name)

    # Wire inputs to the GreaterThan block
    builder.add_link(input_a_name, "out", gt_name, "inA")
    builder.add_link(input_b_name, "out", gt_name, "inB")

    # Wire the GT result to both switches
    builder.add_link(gt_name, "out", max_switch_name, "inSwitch")
    builder.add_link(gt_name, "out", min_switch_name, "inSwitch")

    # --- Max Switch Wiring ---
    builder.add_link(input_a_name, "out", max_switch_name, "inTrue")
    builder.add_link(input_b_name, "out", max_switch_name, "inFalse")

    # --- Min Switch Wiring ---
    builder.add_link(input_b_name, "out", min_switch_name, "inTrue")
    builder.add_link(input_a_name, "out", min_switch_name, "inFalse")

    return (max_switch_name, min_switch_name)


def create_combine_node(
    builder, max1_name, second1_name, max2_name, second2_name, node_id
):
    """
    Creates blocks to find the top two values from two pairs of (max, second_max).
    """
    overall_max, min_of_maxes = create_comparison_node(
        builder, max1_name, max2_name, f"{node_id}_MaxCompare"
    )

    intermediate_second, _ = create_comparison_node(
        builder, min_of_maxes, second1_name, f"{node_id}_Second_A"
    )
    overall_second, _ = create_comparison_node(
        builder, intermediate_second, second2_name, f"{node_id}_Second_B"
    )

    return (overall_max, overall_second)


def main():
    """
    Main function to build and save the .bog file.
    """
    parser = argparse.ArgumentParser(
        description="Build a .bog file to find the N and N-1 max values from 6 damper positions."
    )
    parser.add_argument(
        "-o",
        "--output_dir",
        default="examples",
        help="Output directory for the .bog file.",
    )
    args = parser.parse_args()

    script_filename = os.path.basename(__file__).replace(".py", "")

    builder = BogFolderBuilder("FindTopTwoOfSixDampers")

    inputs = [f"VAV_Damper_{i}" for i in range(1, 7)]
    for i, name in enumerate(inputs):
        builder.add_numeric_writable(name, default_value=float(i * 10))

    builder.add_numeric_writable("HighestDamperPosition")
    builder.add_numeric_writable("SecondHighestDamperPosition")

    builder.start_sub_folder("CalculationLogic")
    print("--- Entered CalculationLogic sub-folder ---")

    print("Building comparison logic tree for 6 inputs...")

    tier1_results = []
    for i in range(3):
        input_a = inputs[i * 2]
        input_b = inputs[i * 2 + 1]
        max_comp, min_comp = create_comparison_node(
            builder, input_a, input_b, f"T1_P{i}"
        )
        tier1_results.append((max_comp, min_comp))

    max1, second1 = tier1_results[0]
    max2, second2 = tier1_results[1]
    tier2_max, tier2_second = create_combine_node(
        builder, max1, second1, max2, second2, "T2_C0"
    )

    last_pair_max, last_pair_second = tier1_results[2]
    final_max, final_second = create_combine_node(
        builder, tier2_max, tier2_second, last_pair_max, last_pair_second, "T3_C0"
    )

    builder.end_sub_folder()

    print(f"\nFinal Max component is '{final_max}'.")
    print(f"Final Second Max component is '{final_second}'.")
    builder.add_link(final_max, "out", "HighestDamperPosition", "in16")
    builder.add_link(final_second, "out", "SecondHighestDamperPosition", "in16")

    bog_filename = f"{script_filename}.bog"
    output_path = os.path.join(args.output_dir, bog_filename)
    os.makedirs(args.output_dir, exist_ok=True)
    builder.save(output_path)
    print(f"\nSuccessfully created Niagara .bog file at: {output_path}")


if __name__ == "__main__":
    main()
