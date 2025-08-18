import sys
import os
import argparse

from bog_builder import BogFolderBuilder


def create_comparison_node(builder, input_a_name, input_b_name, node_id):
    """Creates logic to find the max and min of two inputs."""
    gt_name = f"GT_{node_id}"
    max_switch_name = f"MaxSwitch_{node_id}"
    min_switch_name = f"MinSwitch_{node_id}"

    builder.add_component("kitControl:GreaterThan", gt_name)
    builder.add_numeric_switch(max_switch_name)
    builder.add_numeric_switch(min_switch_name)

    builder.add_link(input_a_name, "out", gt_name, "inA")
    builder.add_link(input_b_name, "out", gt_name, "inB")

    builder.add_link(gt_name, "out", max_switch_name, "inSwitch")
    builder.add_link(gt_name, "out", min_switch_name, "inSwitch")

    builder.add_link(input_a_name, "out", max_switch_name, "inTrue")
    builder.add_link(input_b_name, "out", max_switch_name, "inFalse")

    builder.add_link(input_b_name, "out", min_switch_name, "inTrue")
    builder.add_link(input_a_name, "out", min_switch_name, "inFalse")

    return (max_switch_name, min_switch_name)


def find_max_and_losers(builder, inputs, rank_label):
    """
    Runs a tournament to find the max value among inputs.
    Returns the single max winner and a list of all other participants (the losers).
    """
    if not inputs:
        return None, []

    if len(inputs) == 1:
        return inputs[0], []

    current_inputs = inputs[:]
    losers = []
    round_num = 1

    while len(current_inputs) > 1:
        next_round_winners = []
        for i in range(0, len(current_inputs) - 1, 2):
            input_a = current_inputs[i]
            input_b = current_inputs[i + 1]

            max_node, min_node = create_comparison_node(
                builder, input_a, input_b, f"{rank_label}_R{round_num}_P{i//2}"
            )

            next_round_winners.append(max_node)
            losers.append(min_node)

        if len(current_inputs) % 2 == 1:
            next_round_winners.append(current_inputs[-1])

        current_inputs = next_round_winners
        round_num += 1

    max_winner = current_inputs[0]

    return max_winner, losers


def main():
    parser = argparse.ArgumentParser(
        description="Find top 5 highest values from 15 damper positions and add a selection filter."
    )
    parser.add_argument(
        "-o",
        "--output_dir",
        default="examples",
        help="Output directory for the .bog file.",
    )
    args = parser.parse_args()

    script_filename = os.path.basename(__file__).replace(".py", "")
    builder = BogFolderBuilder("FindTop5Of15Dampers")

    # --- TOP-LEVEL INPUTS ---
    inputs = [f"VAV_Damper_{i}" for i in range(1, 16)]
    for i, name in enumerate(inputs):
        builder.add_numeric_writable(name, default_value=float((i + 1) * 10))

    # G36 trim and respond Ignore Variable
    builder.add_numeric_writable("I_ignore_var", default_value=1.0)

    # --- TOP-LEVEL OUTPUTS ---
    for rank in range(1, 6):
        builder.add_numeric_writable(f"Rank_{rank}_Highest")
    builder.add_numeric_writable("Filtered_Max")

    remaining_candidates = inputs[:]
    top_5_winners = []

    for rank in range(1, 6):
        if not remaining_candidates:
            break

        builder.start_sub_folder(f"Rank_{rank}")

        winner, losers = find_max_and_losers(
            builder, remaining_candidates, f"Rank{rank}"
        )

        builder.end_sub_folder()

        if winner:
            top_5_winners.append(winner)
            builder.add_link(winner, "out", f"Rank_{rank}_Highest", "in16")

        remaining_candidates = losers

    builder.start_sub_folder("SelectionLogic")
    builder.add_numeric_select("Ignore")
    builder.end_sub_folder()

    if top_5_winners:
        print(
            "\nWiring the top 5 winners into the 'Ignore' block inside the 'SelectionLogic' folder..."
        )
        for i, winner_name in enumerate(top_5_winners):
            target_slot = f"in{chr(65 + i)}"
            builder.add_link(winner_name, "out", "Ignore", target_slot)

        builder.add_link("I_ignore_var", "out", "Ignore", "select")
        builder.add_link("Ignore", "out", "Filtered_Max", "in16")

    # --- Save file ---
    bog_filename = f"{script_filename}.bog"
    output_path = os.path.join(args.output_dir, bog_filename)
    os.makedirs(args.output_dir, exist_ok=True)
    builder.save(output_path)
    print(f"\nSuccessfully created Niagara .bog file at: {output_path}")


if __name__ == "__main__":
    main()
