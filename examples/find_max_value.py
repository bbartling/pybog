import sys
import os
import argparse

# Add the 'src' directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.bog_builder import BogFolderBuilder


def create_max_pair(builder, input_a_name, input_b_name, pair_id):
    """
    Creates and links a GreaterThan and NumericSwitch block to find the maximum of two inputs.

    Args:
        builder (BogFolderBuilder): The BOG builder instance.
        input_a_name (str): The name of the first numeric component.
        input_b_name (str): The name of the second numeric component.
        pair_id (str): A unique identifier for this comparison pair.

    Returns:
        str: The name of the NumericSwitch component which outputs the maximum value.
    """
    gt_name = f"GT_{pair_id}"
    switch_name = f"Switch_{pair_id}"

    # Add the necessary logic blocks for the comparison
    builder.add_component("kitControl:GreaterThan", gt_name)
    builder.add_numeric_switch(switch_name)

    # Wire the two inputs to the GreaterThan block
    builder.add_link(input_a_name, "out", gt_name, "inA")
    builder.add_link(input_b_name, "out", gt_name, "inB")

    # Wire the boolean result of the comparison to the switch's selector
    builder.add_link(gt_name, "out", switch_name, "inSwitch")

    # Wire the original inputs to the true/false paths of the switch.
    # If input_a > input_b, the GreaterThan output is true, so we select inTrue (input_a).
    builder.add_link(input_a_name, "out", switch_name, "inTrue")
    builder.add_link(input_b_name, "out", switch_name, "inFalse")

    # The switch now outputs the greater of the two values.
    return switch_name


def main():
    """
    Main function to build and save the .bog file.
    """
    parser = argparse.ArgumentParser(
        description="Build a .bog file to find the max of 10 inputs using only GreaterThan and NumericSwitch blocks."
    )
    # Updated argument to accept an output directory
    parser.add_argument(
        "-o", "--output_dir", default="examples", help="Output directory for the .bog file."
    )
    args = parser.parse_args()

    # 1. Initialize the builder with a name for the logic folder
    builder = BogFolderBuilder("FindMaxValueWithSwitches")

    # 2. Create 10 numeric writable inputs for the VAV boxes
    print("Adding 10 VAV box inputs...")
    inputs = [f"VAV_{i}" for i in range(1, 11)]
    for name in inputs:
        # Set a default value based on the VAV number for easy testing
        builder.add_numeric_writable(name, default_value=float(name.split('_')[1]))

    # 3. Create the final output point
    builder.add_numeric_writable("MaxValue")

    # 4. Build the comparison tree algorithmically
    # This loop creates a "tournament bracket" to find the max value.
    # In each round (tier), it pairs up the winners from the last round.
    print("Building comparison logic tree...")
    current_tier_outputs = inputs[:]
    tier_num = 1
    while len(current_tier_outputs) > 1:
        print(f"  Processing Tier {tier_num} with {len(current_tier_outputs)} inputs...")
        next_tier_outputs = []
        
        # Pair up components from the current tier
        for i in range(len(current_tier_outputs) // 2):
            input_a = current_tier_outputs[i*2]
            input_b = current_tier_outputs[i*2 + 1]
            pair_id = f"T{tier_num}_P{i}"
            
            # Create a comparison block for the pair
            winner = create_max_pair(builder, input_a, input_b, pair_id)
            next_tier_outputs.append(winner)
        
        # If there's an odd number of components, the last one gets a "bye"
        # and passes directly to the next tier.
        if len(current_tier_outputs) % 2 == 1:
            passthrough = current_tier_outputs[-1]
            next_tier_outputs.append(passthrough)
            print(f"    '{passthrough}' passes to the next tier.")
        
        current_tier_outputs = next_tier_outputs
        tier_num += 1

    # 5. Link the final winner of the tournament to the output component
    final_winner = current_tier_outputs[0]
    print(f"\nFinal winner component is '{final_winner}'. Linking to output.")
    builder.add_link(final_winner, "out", "MaxValue", "in16")

    # 6. Define hardcoded filename and construct the full output path
    bog_filename = "find_max_value.bog"
    output_path = os.path.join(args.output_dir, bog_filename)
    
    # Create the output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)
        
    # Save the complete logic to the .bog file
    builder.save(output_path)
    print(f"\nSuccessfully created Niagara .bog file at: {output_path}")


if __name__ == "__main__":
    main()
