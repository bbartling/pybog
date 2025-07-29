import sys
import os
import argparse

# Add the 'src' directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.bog_builder import BogFolderBuilder


def find_max_of_list(builder, input_list, node_id):
    """
    Builds a tournament-style bracket of comparators to find the maximum value from a list of components.

    Args:
        builder (BogFolderBuilder): The BOG builder instance.
        input_list (list): A list of component names to find the maximum of.
        node_id (str): A unique identifier for this max-finding operation.

    Returns:
        str: The name of the component holding the maximum value.
    """
    current_tier_outputs = input_list[:]
    tier_num = 1
    while len(current_tier_outputs) > 1:
        next_tier_outputs = []
        # Pair up components from the current tier
        for i in range(len(current_tier_outputs) // 2):
            input_a = current_tier_outputs[i*2]
            input_b = current_tier_outputs[i*2 + 1]
            pair_id = f"{node_id}_T{tier_num}_P{i}"

            # Create a comparison block for the pair
            gt_name = f"GT_{pair_id}"
            switch_name = f"Switch_{pair_id}"
            builder.add_component("kitControl:GreaterThan", gt_name)
            builder.add_numeric_switch(switch_name)
            builder.add_link(input_a, "out", gt_name, "inA")
            builder.add_link(input_b, "out", gt_name, "inB")
            builder.add_link(gt_name, "out", switch_name, "inSwitch")
            builder.add_link(input_a, "out", switch_name, "inTrue")
            builder.add_link(input_b, "out", switch_name, "inFalse")
            next_tier_outputs.append(switch_name)

        # Pass through the odd component
        if len(current_tier_outputs) % 2 == 1:
            next_tier_outputs.append(current_tier_outputs[-1])

        current_tier_outputs = next_tier_outputs
        tier_num += 1
    return current_tier_outputs[0]

def sanitize_inputs(builder, original_inputs, values_to_exclude, neg_inf_name, node_id):
    """
    Creates logic to replace certain values in a list with negative infinity.

    For each input in original_inputs, it checks if it equals any of the values_to_exclude.
    If it does, it outputs negative infinity. Otherwise, it outputs the original input's value.

    Args:
        builder (BogFolderBuilder): The BOG builder instance.
        original_inputs (list): The list of initial component names.
        values_to_exclude (list): A list of component names whose values should be excluded.
        neg_inf_name (str): The name of the negative infinity NumericConst component.
        node_id (str): A unique identifier for this sanitization operation.

    Returns:
        list: A new list of component names that represent the sanitized outputs.
    """
    sanitized_outputs = []
    for i, original_input in enumerate(original_inputs):
        or_inputs = []
        # Check if the original input equals any of the values to be excluded
        for j, value_to_exclude in enumerate(values_to_exclude):
            eq_name = f"EQ_{node_id}_{i}_vs_{j}"
            builder.add_component("kitControl:Equal", eq_name)
            builder.add_link(original_input, "out", eq_name, "inA")
            builder.add_link(value_to_exclude, "out", eq_name, "inB")
            or_inputs.append(eq_name)

        # Combine all equality checks with OR gates
        last_or_output = or_inputs[0]
        if len(or_inputs) > 1:
            for k in range(len(or_inputs) - 1):
                or_name = f"OR_{node_id}_{i}_{k}"
                builder.add_component("kitControl:Or", or_name)
                builder.add_link(last_or_output, "out", or_name, "inA")
                builder.add_link(or_inputs[k+1], "out", or_name, "inB")
                last_or_output = or_name

        # Use a switch to select the original value or negative infinity
        switch_name = f"SanitizeSwitch_{node_id}_{i}"
        builder.add_numeric_switch(switch_name)
        builder.add_link(last_or_output, "out", switch_name, "inSwitch")
        builder.add_link(neg_inf_name, "out", switch_name, "inTrue") # If equal, exclude it
        builder.add_link(original_input, "out", switch_name, "inFalse") # If not equal, use it
        sanitized_outputs.append(switch_name)

    return sanitized_outputs

def main():
    """
    Main function to build the .bog file.
    """
    parser = argparse.ArgumentParser(
        description="Build a .bog file to find the Nth highest value from 6 damper positions."
    )
    parser.add_argument(
        "-o", "--output_dir", default="examples", help="Output directory for the .bog file."
    )
    args = parser.parse_args()

    # 1. Initialize the builder
    builder = BogFolderBuilder("FindNthOfSixDampers")

    # 2. Create inputs and controls
    vav_inputs = [f"VAV_Damper_{i}" for i in range(1, 7)]
    for i, name in enumerate(vav_inputs):
        builder.add_numeric_writable(name, default_value=float((6-i) * 10))

    builder.add_numeric_writable("Rank_N_Input", default_value=1.0)
    builder.add_numeric_writable("Nth_Highest_Value")
    neg_inf_name = "NegInfinityConst"
    builder.add_component("kitControl:NumericConst", neg_inf_name, properties={"value": -999999.0})

    # 3. Find the sorted values by repeatedly finding the max of a sanitized list
    sorted_values = []
    values_to_exclude = []
    
    print("Generating logic to find sorted values...")
    for i in range(1, 7):
        print(f"  Finding Max {i}...")
        # Start with the raw inputs, then use sanitized lists for subsequent ranks
        list_to_search = vav_inputs
        if i > 1:
            list_to_search = sanitize_inputs(builder, vav_inputs, values_to_exclude, neg_inf_name, f"S{i}")
        
        # Find the max of the current list
        max_n = find_max_of_list(builder, list_to_search, f"Max{i}")
        
        # Store the result and add it to the exclusion list for the next iteration
        sorted_values.append(max_n)
        values_to_exclude.append(max_n)

    # 4. Create the selector logic to pick the Nth value
    print("Generating selector logic...")
    selector_name = "FinalSelector"
    builder.add_component("kitControl:NumericSelect", selector_name)
    builder.add_link("Rank_N_Input", "out", selector_name, "in")
    for i, sorted_val_comp in enumerate(sorted_values):
        builder.add_link(sorted_val_comp, "out", selector_name, f"in{i+1}")

    # 5. Link the selector output to the final output point
    builder.add_link(selector_name, "out", "Nth_Highest_Value", "in16")

    # 6. Save the file
    bog_filename = "find_nth_of_6.bog"
    output_path = os.path.join(args.output_dir, bog_filename)
    os.makedirs(args.output_dir, exist_ok=True)
    builder.save(output_path)
    print(f"\nSuccessfully created Niagara .bog file at: {output_path}")


if __name__ == "__main__":
    main()
