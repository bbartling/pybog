import sys
import os
import argparse

# Add the 'src' directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
# Make sure you are importing the new builder with sub-folder capabilities
from src.bog_builder_new import BogFolderBuilder


def create_max_pair(builder, input_a_name, input_b_name, pair_id):
    """
    Creates and links a GreaterThan and NumericSwitch block to find the maximum of two inputs.
    This function doesn't need to know about sub-folders; it will automatically
    place components in whatever the builder's current "context" is.
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
    builder.add_link(input_a_name, "out", switch_name, "inTrue")
    builder.add_link(input_b_name, "out", switch_name, "inFalse")

    return switch_name


def main():
    """
    Main function to build and save the .bog file.
    """
    parser = argparse.ArgumentParser(
        description="Build a .bog file to find the max of 10 inputs using only GreaterThan and NumericSwitch blocks."
    )
    parser.add_argument(
        "-o", "--output_dir", default="examples", help="Output directory for the .bog file."
    )
    args = parser.parse_args()

    script_filename = os.path.basename(__file__).replace(".py", "")

    # 1. Initialize the builder with a name for the logic folder
    builder = BogFolderBuilder("FindMaxValueWithSwitches")

    # 2. Create TOP-LEVEL inputs and the final output point.
    # These will remain visible on the main wiresheet.
    print("Adding 10 VAV box inputs...")
    inputs = [f"VAV_{i}" for i in range(1, 11)]
    for name in inputs:
        builder.add_numeric_writable(name, default_value=float(name.split('_')[1]))

    builder.add_numeric_writable("MaxValue")


    # TUTORIAL: HOW TO USE SUB-FOLDERS
    # We will place the entire dynamically-generated comparison tree
    # inside a single sub-folder.

    # STEP 1: Start the sub-folder "sandbox".
    builder.start_sub_folder("CalculationLogic")

    # 3. Build the comparison tree algorithmically INSIDE the sub-folder.
    # The while loop and the create_max_pair function will now create all
    # their components inside the "CalculationLogic" folder.
    print("Building comparison logic tree...")
    current_tier_outputs = inputs[:]
    tier_num = 1
    while len(current_tier_outputs) > 1:
        print(f"  Processing Tier {tier_num} with {len(current_tier_outputs)} inputs...")
        next_tier_outputs = []
        
        for i in range(len(current_tier_outputs) // 2):
            input_a = current_tier_outputs[i*2]
            input_b = current_tier_outputs[i*2 + 1]
            pair_id = f"T{tier_num}_P{i}"
            
            # The builder automatically creates proxies for the inputs on the first pass
            winner = create_max_pair(builder, input_a, input_b, pair_id)
            next_tier_outputs.append(winner)
        
        if len(current_tier_outputs) % 2 == 1:
            passthrough = current_tier_outputs[-1]
            next_tier_outputs.append(passthrough)
            print(f"    '{passthrough}' passes to the next tier.")
        
        current_tier_outputs = next_tier_outputs
        tier_num += 1

    # This is the final component inside the sub-folder that holds the max value
    final_winner = current_tier_outputs[0]

    # STEP 2: End the sub-folder "sandbox".
    builder.end_sub_folder()


    # 4. Link the final winner to the output component.
    # The builder sees that 'final_winner' is inside the sub-folder and 'MaxValue'
    # is outside, so it will automatically create a ProxyOut point.
    print(f"\nFinal winner component is '{final_winner}'. Linking to output.")
    builder.add_link(final_winner, "out", "MaxValue", "in16")

    # 5. Save the file.
    bog_filename = f"{script_filename}.bog"
    output_path = os.path.join(args.output_dir, bog_filename)
    os.makedirs(args.output_dir, exist_ok=True)
    builder.save(output_path)
    print(f"\nSuccessfully created Niagara .bog file at: {output_path}")


if __name__ == "__main__":
    main()
