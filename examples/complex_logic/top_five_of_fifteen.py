import sys
import os
import argparse

# Add 'src' to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.bog_builder_new import BogFolderBuilder


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
            
            # Create comparison and get both the max (winner) and min (loser)
            max_node, min_node = create_comparison_node(builder, input_a, input_b, f"{rank_label}_R{round_num}_P{i//2}")
            
            next_round_winners.append(max_node)
            losers.append(min_node)  # Collect the loser of the pair
        
        # Handle an odd number of inputs in the current round
        if len(current_inputs) % 2 == 1:
            # The last element passes through to the next round of winners
            next_round_winners.append(current_inputs[-1])
            
        current_inputs = next_round_winners
        round_num += 1
    
    # The final winner is the only component left
    max_winner = current_inputs[0]
    
    return max_winner, losers


def main():
    parser = argparse.ArgumentParser(description="Find top 5 highest values from 15 damper positions.")
    parser.add_argument("-o", "--output_dir", default="examples", help="Output directory for the .bog file.")
    args = parser.parse_args()

    script_filename = os.path.basename(__file__).replace(".py", "")
    builder = BogFolderBuilder("FindTop5Of15Dampers")

    # Inputs: 15 dampers
    inputs = [f"VAV_Damper_{i}" for i in range(1, 16)]
    for i, name in enumerate(inputs):
        builder.add_numeric_writable(name, default_value=float((i + 1) * 10))

    # Outputs: Top 5 winners
    for rank in range(1, 6):
        builder.add_numeric_writable(f"Rank_{rank}_Highest")

    # Start with the full list of initial inputs
    remaining_candidates = inputs[:]

    # Build top 5 ranking logic
    for rank in range(1, 6):
        # Stop if there are no more candidates to rank
        if not remaining_candidates:
            break
            
        builder.start_sub_folder(f"Rank_{rank}")
        
        # Find the winner and the list of losers from the current candidates
        winner, losers = find_max_and_losers(builder, remaining_candidates, f"Rank{rank}")
        
        builder.end_sub_folder()
        
        # Link the winner of this tournament to the corresponding rank output
        if winner:
            builder.add_link(winner, "out", f"Rank_{rank}_Highest", "in16")
        
        # The inputs for the next tournament are the losers from this one
        remaining_candidates = losers

    # Save file
    bog_filename = f"{script_filename}.bog"
    output_path = os.path.join(args.output_dir, bog_filename)
    os.makedirs(args.output_dir, exist_ok=True)
    builder.save(output_path)
    print(f"\nSuccessfully created Niagara .bog file at: {output_path}")


if __name__ == "__main__":
    main()