import sys
import os
import argparse

# Add the 'src' directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.bog_builder_new import BogFolderBuilder


def create_max_pair(builder, input_a, input_b, pair_id):
    """Creates GT and NumericSwitch blocks to select the max of two inputs."""
    gt_name = f"GT_{pair_id}"
    switch_name = f"MaxSwitch_{pair_id}"

    builder.add_component("kitControl:GreaterThan", gt_name)
    builder.add_numeric_switch(switch_name)

    builder.add_link(input_a, "out", gt_name, "inA")
    builder.add_link(input_b, "out", gt_name, "inB")
    builder.add_link(gt_name, "out", switch_name, "inSwitch")
    builder.add_link(input_a, "out", switch_name, "inTrue")
    builder.add_link(input_b, "out", switch_name, "inFalse")

    return switch_name


def main():
    parser = argparse.ArgumentParser(description="Find Nth max value from 10 VAV damper positions.")
    parser.add_argument("-o", "--output_dir", default="examples", help="Output directory.")
    args = parser.parse_args()

    script_filename = os.path.basename(__file__).replace(".py", "")
    builder = BogFolderBuilder("FindNthDamper")

    # === Top-Level Inputs ===
    inputs = [f"VAV_Damper_{i}" for i in range(1, 11)]
    for i, name in enumerate(inputs, start=1):
        builder.add_numeric_writable(name, default_value=float(i * 10))

    # Adjustable N selector
    builder.add_numeric_writable("Select_N", default_value=1.0)  # Adjust N from wiresheet

    # Final output
    builder.add_numeric_writable("Nth_Damper_Position")

    # === Sub-folder for ranked calculation logic ===
    builder.start_sub_folder("RankedMaxValues")

    current_inputs = inputs[:]
    ranked_outputs = []

    # Rank all inputs (full sort approach)
    for rank_num in range(len(inputs)):
        rank_folder = f"Rank_{rank_num+1}"
        builder.start_sub_folder(rank_folder)

        tier_outputs = current_inputs[:]
        tier_num = 1
        while len(tier_outputs) > 1:
            next_tier = []
            for i in range(0, len(tier_outputs), 2):
                if i + 1 < len(tier_outputs):
                    winner = create_max_pair(builder, tier_outputs[i], tier_outputs[i+1],
                                             f"R{rank_num+1}_T{tier_num}_P{i//2}")
                    next_tier.append(winner)
                else:
                    next_tier.append(tier_outputs[i])  # Odd carry-over
            tier_outputs = next_tier
            tier_num += 1

        # Final winner for this rank
        winner = tier_outputs[0]
        ranked_outputs.append(winner)

        # Remove the winner from the pool for next ranking pass
        current_inputs = [inp for inp in current_inputs if inp != winner]

        builder.end_sub_folder()

    # === NumericSelect to choose Nth max ===
    builder.add_component("kitControl:NumericSelect", "Nth_Select")
    for idx, winner in enumerate(ranked_outputs, start=1):
        builder.add_link(winner, "out", "Nth_Select", f"in{idx}")

    # Link N selector
    builder.add_link("Select_N", "out", "Nth_Select", "inIndex")
    builder.end_sub_folder()

    # Final output link
    builder.add_link("Nth_Select", "out", "Nth_Damper_Position", "in16")

    # === Save ===
    bog_filename = f"{script_filename}.bog"
    output_path = os.path.join(args.output_dir, bog_filename)
    os.makedirs(args.output_dir, exist_ok=True)
    builder.save(output_path)
    print(f"\nSuccessfully created Niagara .bog file at: {output_path}")


if __name__ == "__main__":
    main()
