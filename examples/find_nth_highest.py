import sys
import os
import argparse

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.bog_builder import BogFolderBuilder

def create_max_pair(builder, input_a, input_b, pair_id):
    """Pairwise GreaterThan + Switch to find max."""
    gt = f"GT_{pair_id}"
    sw = f"Switch_{pair_id}"
    builder.add_component("kitControl:GreaterThan", gt)
    builder.add_numeric_switch(sw)
    builder.add_link(input_a, "out", gt, "inA")
    builder.add_link(input_b, "out", gt, "inB")
    builder.add_link(gt, "out", sw, "inSwitch")
    builder.add_link(input_a, "out", sw, "inTrue")
    builder.add_link(input_b, "out", sw, "inFalse")
    return sw

def find_max(builder, inputs, tier_prefix):
    """Tournament bracket max finder."""
    current = inputs[:]
    tier = 1
    while len(current) > 1:
        next_round = []
        for i in range(len(current)//2):
            a, b = current[i*2], current[i*2+1]
            winner = create_max_pair(builder, a, b, f"{tier_prefix}_T{tier}_P{i}")
            next_round.append(winner)
        if len(current) % 2 == 1:
            next_round.append(current[-1])  # odd pass-through
        current = next_round
        tier += 1
    return current[0]

def main():
    parser = argparse.ArgumentParser(description="Find dynamic Nth highest using NumericWritable N.")
    parser.add_argument("-o", "--output_dir", default="examples", help="Output directory for .bog file")
    args = parser.parse_args()

    builder = BogFolderBuilder("DynamicNthHighest")

    # 1. Create VAV damper inputs
    vav_inputs = [f"VAV_{i}" for i in range(1, 11)]
    for name in vav_inputs:
        builder.add_numeric_writable(name, default_value=float(name.split("_")[1]))

    # 2. Add NumericWritable input for "N"
    builder.add_numeric_writable("Rank_N", default_value=1)

    # 3. Precompute all ranks (Top 1..10)
    remaining = vav_inputs[:]
    rank_outputs = []
    for rank in range(1, len(vav_inputs) + 1):
        winner = find_max(builder, remaining, f"Rank{rank}")
        rank_outputs.append(winner)
        if winner in remaining:
            remaining.remove(winner)

    # 4. Build NumericSwitch ladder for N selection
    last_switch = rank_outputs[0]
    for i, comp in enumerate(rank_outputs[1:], start=2):
        switch_name = f"N_Select_{i}"
        builder.add_numeric_switch(switch_name)
        builder.add_link("Rank_N", "out", switch_name, "inSwitch")
        builder.add_link(last_switch, "out", switch_name, "inFalse")
        builder.add_link(comp, "out", switch_name, "inTrue")
        last_switch = switch_name

    # 5. Output final Nth highest value
    builder.add_numeric_writable("Nth_Highest_Value")
    builder.add_link(last_switch, "out", "Nth_Highest_Value", "in16")

    os.makedirs(args.output_dir, exist_ok=True)
    output_path = os.path.join(args.output_dir, "find_nth_highest.bog")
    builder.save(output_path)
    print(f"✅ Created: {output_path}")

if __name__ == "__main__":
    main()
