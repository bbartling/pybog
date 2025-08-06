import sys
import os
import argparse

# Add 'src' to Python path
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
    parser = argparse.ArgumentParser(description="Find Nth max value from 10 VAV damper positions (fully explicit fall-down).")
    parser.add_argument("-o", "--output_dir", default="examples", help="Output directory.")
    args = parser.parse_args()

    script_filename = os.path.basename(__file__).replace(".py", "")
    builder = BogFolderBuilder("FindNthDamper_FallDown")

    # === Top-Level Inputs ===
    inputs = [f"VAV_Damper_{i}" for i in range(1, 11)]
    for i, name in enumerate(inputs, start=1):
        builder.add_numeric_writable(name, default_value=float(i * 10))

    # Adjustable N selector
    builder.add_numeric_writable("Select_N", default_value=1.0)
    builder.add_numeric_writable("Nth_Damper_Position")

    # === RankedMaxValues Folder ===
    builder.start_sub_folder("RankedMaxValues")

    # ------------------------
    # RANK 1
    # ------------------------
    builder.start_sub_folder("Rank_1")
    r1_t1_p0 = create_max_pair(builder, "VAV_Damper_1", "VAV_Damper_2", "R1_T1_P0")
    r1_t1_p1 = create_max_pair(builder, "VAV_Damper_3", "VAV_Damper_4", "R1_T1_P1")
    r1_t1_p2 = create_max_pair(builder, "VAV_Damper_5", "VAV_Damper_6", "R1_T1_P2")
    r1_t1_p3 = create_max_pair(builder, "VAV_Damper_7", "VAV_Damper_8", "R1_T1_P3")
    r1_t1_p4 = create_max_pair(builder, "VAV_Damper_9", "VAV_Damper_10", "R1_T1_P4")

    r1_t2_p0 = create_max_pair(builder, r1_t1_p0, r1_t1_p1, "R1_T2_P0")
    r1_t2_p1 = create_max_pair(builder, r1_t1_p2, r1_t1_p3, "R1_T2_P1")

    r1_t3_p0 = create_max_pair(builder, r1_t2_p0, r1_t2_p1, "R1_T3_P0")
    r1_winner = create_max_pair(builder, r1_t3_p0, r1_t1_p4, "R1_T4_P0")
    builder.end_sub_folder()

    # Remaining inputs for Rank 2
    r2_inputs = [i for i in inputs if i not in [r1_winner]]

    # ------------------------
    # RANK 2
    # ------------------------
    builder.start_sub_folder("Rank_2")
    r2_t1_p0 = create_max_pair(builder, r2_inputs[0], r2_inputs[1], "R2_T1_P0")
    r2_t1_p1 = create_max_pair(builder, r2_inputs[2], r2_inputs[3], "R2_T1_P1")
    r2_t1_p2 = create_max_pair(builder, r2_inputs[4], r2_inputs[5], "R2_T1_P2")
    r2_t1_p3 = create_max_pair(builder, r2_inputs[6], r2_inputs[7], "R2_T1_P3")
    r2_t1_p4 = r2_inputs[8]  # Single leftover

    r2_t2_p0 = create_max_pair(builder, r2_t1_p0, r2_t1_p1, "R2_T2_P0")
    r2_t2_p1 = create_max_pair(builder, r2_t1_p2, r2_t1_p3, "R2_T2_P1")

    r2_t3_p0 = create_max_pair(builder, r2_t2_p0, r2_t2_p1, "R2_T3_P0")
    r2_winner = create_max_pair(builder, r2_t3_p0, r2_t1_p4, "R2_T4_P0")
    builder.end_sub_folder()

    # Remaining inputs for Rank 3
    r3_inputs = [i for i in r2_inputs if i not in [r2_winner]]

    # ------------------------
    # RANK 3
    # ------------------------
    builder.start_sub_folder("Rank_3")
    r3_t1_p0 = create_max_pair(builder, r3_inputs[0], r3_inputs[1], "R3_T1_P0")
    r3_t1_p1 = create_max_pair(builder, r3_inputs[2], r3_inputs[3], "R3_T1_P1")
    r3_t1_p2 = create_max_pair(builder, r3_inputs[4], r3_inputs[5], "R3_T1_P2")
    r3_t1_p3 = r3_inputs[6]  # Odd leftover

    r3_t2_p0 = create_max_pair(builder, r3_t1_p0, r3_t1_p1, "R3_T2_P0")
    r3_t2_p1 = create_max_pair(builder, r3_t1_p2, r3_t1_p3, "R3_T2_P1")

    r3_winner = create_max_pair(builder, r3_t2_p0, r3_t2_p1, "R3_T3_P0")
    builder.end_sub_folder()

    # Remaining inputs for Rank 4
    r4_inputs = [i for i in r3_inputs if i not in [r3_winner]]

    # ------------------------
    # RANK 4
    # ------------------------
    builder.start_sub_folder("Rank_4")
    r4_t1_p0 = create_max_pair(builder, r4_inputs[0], r4_inputs[1], "R4_T1_P0")
    r4_t1_p1 = create_max_pair(builder, r4_inputs[2], r4_inputs[3], "R4_T1_P1")
    r4_t1_p2 = r4_inputs[4]  # Odd leftover

    r4_t2_p0 = create_max_pair(builder, r4_t1_p0, r4_t1_p1, "R4_T2_P0")
    r4_winner = create_max_pair(builder, r4_t2_p0, r4_t1_p2, "R4_T3_P0")
    builder.end_sub_folder()

    # Remaining inputs for Rank 5
    r5_inputs = [i for i in r4_inputs if i not in [r4_winner]]

    # ------------------------
    # RANK 5
    # ------------------------
    builder.start_sub_folder("Rank_5")
    r5_t1_p0 = create_max_pair(builder, r5_inputs[0], r5_inputs[1], "R5_T1_P0")
    r5_t1_p1 = create_max_pair(builder, r5_inputs[2], r5_inputs[3], "R5_T1_P1")
    r5_winner = create_max_pair(builder, r5_t1_p0, r5_t1_p1, "R5_T2_P0")
    builder.end_sub_folder()

    # Remaining inputs for Rank 6
    r6_inputs = [i for i in r5_inputs if i not in [r5_winner]]

    # ------------------------
    # RANK 6
    # ------------------------
    builder.start_sub_folder("Rank_6")
    r6_t1_p0 = create_max_pair(builder, r6_inputs[0], r6_inputs[1], "R6_T1_P0")
    r6_t1_p1 = create_max_pair(builder, r6_inputs[2], r6_inputs[3], "R6_T1_P1")
    r6_winner = create_max_pair(builder, r6_t1_p0, r6_t1_p1, "R6_T2_P0")
    builder.end_sub_folder()

    # Remaining inputs for Rank 7
    r7_inputs = [i for i in r6_inputs if i not in [r6_winner]]

    # ------------------------
    # RANK 7
    # ------------------------
    builder.start_sub_folder("Rank_7")
    r7_t1_p0 = create_max_pair(builder, r7_inputs[0], r7_inputs[1], "R7_T1_P0")
    r7_winner = create_max_pair(builder, r7_t1_p0, r7_inputs[2], "R7_T2_P0")
    builder.end_sub_folder()

    # Remaining inputs for Rank 8
    r8_inputs = [i for i in r7_inputs if i not in [r7_winner]]

    # ------------------------
    # RANK 8
    # ------------------------
    builder.start_sub_folder("Rank_8")
    r8_winner = create_max_pair(builder, r8_inputs[0], r8_inputs[1], "R8_T1_P0")
    builder.end_sub_folder()

    # Remaining inputs for Rank 9
    r9_inputs = [i for i in r8_inputs if i not in [r8_winner]]

    # ------------------------
    # RANK 9
    # ------------------------
    builder.start_sub_folder("Rank_9")
    r9_winner = r9_inputs[0]  # Single remaining
    builder.end_sub_folder()

    # ------------------------
    # RANK 10 (last damper is lowest)
    # ------------------------
    builder.start_sub_folder("Rank_10")
    r10_winner = r9_inputs[0]  # Already lowest
    builder.end_sub_folder()

    # === NumericSelect to choose N ===
    builder.add_numeric_select("Nth_Select")

    # Link winners to A-J slots
    builder.add_link(r1_winner, "out", "Nth_Select", "inA")
    builder.add_link(r2_winner, "out", "Nth_Select", "inB")
    builder.add_link(r3_winner, "out", "Nth_Select", "inC")
    builder.add_link(r4_winner, "out", "Nth_Select", "inD")
    builder.add_link(r5_winner, "out", "Nth_Select", "inE")
    builder.add_link(r6_winner, "out", "Nth_Select", "inF")
    builder.add_link(r7_winner, "out", "Nth_Select", "inG")
    builder.add_link(r8_winner, "out", "Nth_Select", "inH")
    builder.add_link(r9_winner, "out", "Nth_Select", "inI")
    builder.add_link(r10_winner, "out", "Nth_Select", "inJ")

    # Link the Select_N input
    builder.add_link("Select_N", "out", "Nth_Select", "select")

    builder.end_sub_folder()

    # Final Output Link
    builder.add_link("Nth_Select", "out", "Nth_Damper_Position", "in16")

    # Save
    bog_filename = f"{script_filename}.bog"
    output_path = os.path.join(args.output_dir, bog_filename)
    os.makedirs(args.output_dir, exist_ok=True)
    builder.save(output_path)
    print(f"\nSuccessfully created Niagara .bog file at: {output_path}")


if __name__ == "__main__":
    main()
