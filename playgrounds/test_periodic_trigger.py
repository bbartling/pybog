"""
Creates a custom periodic trigger or interval timer. The logic adds a 'Step'
value to a 'Counter' every 5 seconds, but only while the counter is less than
a 'Target' value. This demonstrates a "do-while" loop constructed with
feedback logic, delays, and comparison blocks, which is a powerful pattern
for creating custom timed or sequential operations.
"""

import sys, os, argparse

from bog_builder import BogFolderBuilder

T_MS = "5000"


def main():
    parser = argparse.ArgumentParser(
        description="DIY interval: add 5 every 5s until Counter >= 20 (unit-delay fixed)"
    )
    parser.add_argument(
        "-o", "--output_dir", default="examples", help="Output directory."
    )
    args = parser.parse_args()

    script_filename = os.path.basename(__file__).replace(".py", "")
    b = BogFolderBuilder("Test_Interval_DIY_ForLoop_Fixed")

    # ---------------- TOP-LEVEL I/O ----------------
    b.add_boolean_writable("Enable", True)
    b.add_numeric_writable("Counter", 0.0)
    b.add_numeric_writable("Step", 5.0)
    b.add_numeric_writable("Target", 20.0)
    b.add_numeric_writable("Counter_Out", 0.0)

    # --------------- SUBFOLDER: Interval ---------------
    b.start_sub_folder("Interval")
    b.add_boolean_delay("TickDelay", on_delay=T_MS)
    b.add_one_shot("TickPulse")
    b.add_not("PulseNot")
    b.add_and("Enable_AND_Hold")
    b.end_sub_folder()

    # --------------- SUBFOLDER: Compare ---------------
    b.start_sub_folder("Compare")
    b.add_greater_than_equal("Reached_GE_Target")
    b.add_not("NotReached")
    b.add_and("Enable_AND_NotReached")
    b.end_sub_folder()

    # --------------- SUBFOLDER: Increment ---------------
    b.start_sub_folder("Increment")
    b.add_add("CounterPlusStep")
    b.add_numeric_delay("UnitDelay", update_time="10")
    b.add_numeric_switch("PulseGate")
    b.end_sub_folder()

    b.start_sub_folder("OutputStage")
    b.add_numeric_switch("ReachedHold")
    b.end_sub_folder()

    # -------------------- WIRING --------------------

    b.add_link("Counter", "out", "Reached_GE_Target", "inA")
    b.add_link("Target", "out", "Reached_GE_Target", "inB")
    b.add_link("Reached_GE_Target", "out", "NotReached", "in")
    b.add_link("Enable", "out", "Enable_AND_NotReached", "inA")
    b.add_link("NotReached", "out", "Enable_AND_NotReached", "inB")

    b.add_link("Enable_AND_NotReached", "out", "Enable_AND_Hold", "inA")
    b.add_link("PulseNot", "out", "Enable_AND_Hold", "inB")
    b.add_link("Enable_AND_Hold", "out", "TickDelay", "in")
    b.add_link("TickDelay", "out", "TickPulse", "in")
    b.add_link("TickPulse", "out", "PulseNot", "in")

    b.add_link("Counter", "out", "UnitDelay", "in")
    b.add_link("UnitDelay", "out", "CounterPlusStep", "inA")
    b.add_link("Step", "out", "CounterPlusStep", "inB")

    b.add_link("TickPulse", "out", "PulseGate", "inSwitch")
    b.add_link("CounterPlusStep", "out", "PulseGate", "inTrue")
    b.add_link("UnitDelay", "out", "PulseGate", "inFalse")

    b.add_link("PulseGate", "out", "Counter", "in16")
    b.add_link("Counter", "out", "Counter_Out", "in16")

    # -------------------- SAVE ---------------------
    bog_filename = f"{script_filename}.bog"
    output_path = os.path.join(args.output_dir, bog_filename)
    os.makedirs(args.output_dir, exist_ok=True)
    b.save(output_path)
    print(f"\nCreated: {output_path}")


if __name__ == "__main__":
    main()
