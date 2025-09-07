"""
kitControl:LeadLagCycles Advanced Pump Playground (with Sub-Folder)
-------------------------------------------------------------------

This script creates an advanced demonstration for the kitControl:LeadLagCycles
component, configured for a four-pump sequencing application with realistic
feedback and internal cycle counting.

All the core calculation logic is organized into a 'Logic' sub-folder to
keep the top-level view clean and focused on the main inputs and outputs.

Use in Central Plant staging for chiller, boilers, pumps, etc.
For sim purposes "maxRuntime": "20s" but real world weekly rotation
is more typical.

Algorithm:
- A master 'Pump_Enable' signal is fed into the 'in' slot of the
  LeadLagCycles block inside the 'Logic' folder.
- The block is configured for four outputs ('numberOutputs' = 4).
- The outputs of the block command four individual pumps (represented by
  BooleanWritables at the top level).
- Each pump command is also wired to the 'countUp' slot of a dedicated
  'kitControl:Counter' block inside the 'Logic' folder.
- The output of each counter is wired back into the corresponding 'cycleCount'
  slot on the LeadLagCycles block.
- The four pump commands are combined with an 'Or' block to create a single
  'status' signal, which is wired back to the 'feedback' slot.
- Configurable timers for 'maxRuntime', 'feedbackDelay', and 'clearAlarmTime'
  are included as component properties.
"""

import os
import argparse
from bog_builder import BogFolderBuilder


def main():
    """
    Main function to build and save the LeadLagCycles playground .bog file.
    """
    parser = argparse.ArgumentParser(
        description="Build an advanced .bog file to demonstrate the kitControl:LeadLagCycles component with sub-folders."
    )
    parser.add_argument(
        "-o",
        "--output_dir",
        default="examples",
        help="Output directory for the .bog file.",
    )
    args = parser.parse_args()

    script_filename = os.path.basename(__file__).replace(".py", "")
    builder = BogFolderBuilder("LeadLagCyclesPlayground", debug=True)

    print("--- Creating Top-Level I/O Components ---")

    # --- Inputs & Outputs (at the root level) ---
    builder.add_boolean_writable("Pump_Enable", default_value=False)
    pump_names = ["A", "B", "C", "D"]
    for pump in pump_names:
        # These are the final commands that would go to physical equipment.
        builder.add_boolean_writable(f"Pump_{pump}_Cmd")

    # --- Logic Components (organized inside a sub-folder) ---
    print("\n--- Creating Logic Components inside 'Logic' sub-folder ---")
    builder.start_sub_folder("Logic")

    # The LeadLagCycles component is the core of the logic.
    lead_lag_properties = {
        "numberOutputs": 4,
        "maxRuntime": "20s",
        "feedbackDelay": "10s",
        "clearAlarmTime": "1m",
    }
    builder.add_lead_lag_cycles("Pump_LeadLag", properties=lead_lag_properties)

    # The Counter for each pump is also part of the internal logic.
    for pump in pump_names:
        builder.add_counter(f"Pump_{pump}_Counter")

    # The Feedback logic is internal to the calculation as well.
    builder.add_or("Feedback_Or")

    builder.end_sub_folder()
    print("--- Exited 'Logic' sub-folder ---")

    print("\n--- Wiring Components (cross-folder links are handled automatically) ---")

    # Wire the master enable signal from the root level to the logic block.
    builder.add_link("Pump_Enable", "out", "Pump_LeadLag", "in")

    # Wire the feedback loop from the root-level commands back to the logic folder.
    builder.add_link("Pump_A_Cmd", "out", "Feedback_Or", "inA")
    builder.add_link("Pump_B_Cmd", "out", "Feedback_Or", "inB")
    builder.add_link("Pump_C_Cmd", "out", "Feedback_Or", "inC")
    builder.add_link("Pump_D_Cmd", "out", "Feedback_Or", "inD")
    builder.add_link("Feedback_Or", "out", "Pump_LeadLag", "feedback")

    # Wire each pump's command, counter, and cycle count feedback.
    for pump in pump_names:
        # Wire from the logic block out to the final pump command at the root level.
        builder.add_link(f"Pump_LeadLag", f"out{pump}", f"Pump_{pump}_Cmd", "in16")

        # Wire the logic block's output to its corresponding internal counter.
        builder.add_link(
            f"Pump_LeadLag", f"out{pump}", f"Pump_{pump}_Counter", "countUp"
        )

        # Wire the internal counter's value back to the logic block's cycle count input.
        builder.add_link(
            f"Pump_{pump}_Counter", "out", f"Pump_LeadLag", f"cycleCount{pump}"
        )

    # --- Save the .bog file ---
    bog_filename = f"{script_filename}.bog"
    output_path = os.path.join(args.output_dir, bog_filename)
    os.makedirs(args.output_dir, exist_ok=True)
    builder.save(output_path)

    print(
        f"\nSuccessfully created Niagara .bog file at: {os.path.abspath(output_path)}"
    )
    print("Drag this file into Niagara Workbench to test the logic.")


if __name__ == "__main__":
    main()
