"""
Generic 2-Pump Rotator with Auto-Failover without kitControl widget
Does not require calculating run hours and can be manually
linked up to a schedule to rotate when central plant is off which
humans may like better than kitControl rotatation widgets that can
rotate equipment at random including peak central plant loads and cause
lots of havoc and angry clients.

This script builds a robust pump sequencing and failover wiresheet using
fundamental logic blocks. It avoids specialized components, providing an
explicit and clear control sequence.

This revised version replaces the `BooleanLatch` component with a classic
Set-Reset (SR) latch built from basic OR and AND gates. This provides a
more fundamental and transparent implementation of the failure memory.

Algorithm:
1.  **Lead Selection**: A top-level boolean, 'Pump_1_Lead_Select', determines
    the desired lead pump. If true, Pump 1 is lead; if false, Pump 2 is lead.
2.  **Command Generation**: When the 'System_Enable' signal is true, a command
    is sent to the designated lead pump, provided it is not in a failure state.
3.  **Failure Detection**:
    - For each pump, the logic checks if a command has been sent (`Pump_Cmd`)
      but the status feedback (`Pump_Status`) has not become true.
    - If this condition (Cmd ON, Status OFF) persists for 60 seconds (configurable),
      the pump is considered to be in a failure state.
4.  **Failure Latching (SR Latch)**:
    - Once a failure is detected, an SR latch constructed from logic gates
      locks the pump in a failure state, preventing it from being commanded again.
    - This also illuminates a top-level 'Pump_Failure_Alarm' boolean.
    - The failure state can only be cleared by a 'Manual_Reset' signal or by
      disabling the entire system.
5.  **Automatic Failover**:
    - If the designated lead pump enters a failure state, the logic
      automatically stops commanding it and sends a command to the lag pump
      to take over.
"""

import sys
import os
import argparse

# The script must append the path to the bog_builder library.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))
from bog_builder import BogFolderBuilder


def main():
    """
    Main function to build and save the generic pump rotator .bog file.
    """
    parser = argparse.ArgumentParser(
        description="Build a .bog file for a generic 2-pump rotator with auto-failover."
    )
    parser.add_argument(
        "-o",
        "--output_dir",
        default="examples",
        help="Output directory for the .bog file.",
    )
    args = parser.parse_args()

    builder = BogFolderBuilder("Generic_Pump_Rotator_With_Failover", debug=True)

    # --- Top-Level I/O and Configuration ---
    print("--- Creating Top-Level Inputs & Outputs ---")
    builder.add_boolean_writable("System_Enable", default_value=False)
    builder.add_boolean_writable("Pump_1_Lead_Select", default_value=True)
    builder.add_boolean_writable("Manual_Reset", default_value=False)

    builder.add_boolean_writable("Pump_1_Status", default_value=False)
    builder.add_boolean_writable("Pump_2_Status", default_value=False)

    builder.add_boolean_writable("Pump_1_Cmd", default_value=False)
    builder.add_boolean_writable("Pump_2_Cmd", default_value=False)
    builder.add_boolean_writable("Pump_1_Failure_Alarm", default_value=False)
    builder.add_boolean_writable("Pump_2_Failure_Alarm", default_value=False)

    # --- Logic Components (organized in a sub-folder) ---
    print("\n--- Creating Logic Components ---")
    builder.start_sub_folder("PumpControlLogic")

    # REVISED: Lead Pump Selection using fundamental gates
    builder.add_not("Pump_2_Is_Lead_Calc")
    builder.add_and("P1_Lead_Cmd_Request")
    builder.add_and("P2_Lead_Cmd_Request")

    # Final Command Generation (before interlocks)
    builder.add_or("Final_Cmd_Logic_P1")
    builder.add_or("Final_Cmd_Logic_P2")
    builder.add_and("Normal_Run_Cmd_P1")
    builder.add_and("Normal_Run_Cmd_P2")
    builder.add_and("Failover_Run_Cmd_P1")
    builder.add_and("Failover_Run_Cmd_P2")

    # Failure Detection
    builder.add_not("Pump_1_Status_Not")
    builder.add_not("Pump_2_Status_Not")
    builder.add_and("Pump_1_Fail_Condition")
    builder.add_and("Pump_2_Fail_Condition")
    builder.add_boolean_delay("Pump_1_Fail_Timer", on_delay="60s")
    builder.add_boolean_delay("Pump_2_Fail_Timer", on_delay="60s")

    # --- NEW: Failure Latching and Reset using SR Latch ---
    # Pump 1 SR Latch
    builder.add_or("P1_Latch_Set_Logic")
    builder.add_not("P1_Reset_Condition")
    builder.add_and("Pump_1_In_Failure")  # This AND gate is the latch's memory

    # Pump 2 SR Latch
    builder.add_or("P2_Latch_Set_Logic")
    builder.add_not("P2_Reset_Condition")
    builder.add_and("Pump_2_In_Failure")  # This AND gate is the latch's memory

    # Shared Reset Logic
    builder.add_or("Reset_Signal_P1")
    builder.add_or("Reset_Signal_P2")
    builder.add_not("System_Is_Off")

    builder.end_sub_folder()

    # --- Component Wiring ---
    print("\n--- Wiring Components ---")

    # 1. REVISED: Wire the Lead Pump Selector Logic
    builder.add_link("Pump_1_Lead_Select", "out", "Pump_2_Is_Lead_Calc", "in")

    builder.add_link("System_Enable", "out", "P1_Lead_Cmd_Request", "inA")
    builder.add_link("Pump_1_Lead_Select", "out", "P1_Lead_Cmd_Request", "inB")

    builder.add_link("System_Enable", "out", "P2_Lead_Cmd_Request", "inA")
    builder.add_link("Pump_2_Is_Lead_Calc", "out", "P2_Lead_Cmd_Request", "inB")

    # 2. Wire the Failure Detection Logic for each pump
    # Pump 1 Failure Detection
    builder.add_link("Pump_1_Status", "out", "Pump_1_Status_Not", "in")
    builder.add_link("Pump_1_Cmd", "out", "Pump_1_Fail_Condition", "inA")
    builder.add_link("Pump_1_Status_Not", "out", "Pump_1_Fail_Condition", "inB")
    builder.add_link("Pump_1_Fail_Condition", "out", "Pump_1_Fail_Timer", "in")

    # Pump 2 Failure Detection
    builder.add_link("Pump_2_Status", "out", "Pump_2_Status_Not", "in")
    builder.add_link("Pump_2_Cmd", "out", "Pump_2_Fail_Condition", "inA")
    builder.add_link("Pump_2_Status_Not", "out", "Pump_2_Fail_Condition", "inB")
    builder.add_link("Pump_2_Fail_Condition", "out", "Pump_2_Fail_Timer", "in")

    # 3. --- NEW: Wire the SR Latch for Failure Memory ---
    # Latch Logic: Output = (Set OR Output_Feedback) AND (NOT Reset)
    builder.add_link("System_Enable", "out", "System_Is_Off", "in")

    # Pump 1 SR Latch Wiring
    builder.add_link(
        "Pump_1_Fail_Timer", "out", "P1_Latch_Set_Logic", "inA"
    )  # Set signal
    builder.add_link(
        "Pump_1_In_Failure", "out", "P1_Latch_Set_Logic", "inB"
    )  # Feedback for latching
    builder.add_link("Manual_Reset", "out", "Reset_Signal_P1", "inA")
    builder.add_link("System_Is_Off", "out", "Reset_Signal_P1", "inB")
    builder.add_link(
        "Reset_Signal_P1", "out", "P1_Reset_Condition", "in"
    )  # Reset signal
    builder.add_link("P1_Latch_Set_Logic", "out", "Pump_1_In_Failure", "inA")
    builder.add_link("P1_Reset_Condition", "out", "Pump_1_In_Failure", "inB")

    # Pump 2 SR Latch Wiring
    builder.add_link(
        "Pump_2_Fail_Timer", "out", "P2_Latch_Set_Logic", "inA"
    )  # Set signal
    builder.add_link(
        "Pump_2_In_Failure", "out", "P2_Latch_Set_Logic", "inB"
    )  # Feedback for latching
    builder.add_link("Manual_Reset", "out", "Reset_Signal_P2", "inA")
    builder.add_link("System_Is_Off", "out", "Reset_Signal_P2", "inB")
    builder.add_link(
        "Reset_Signal_P2", "out", "P2_Reset_Condition", "in"
    )  # Reset signal
    builder.add_link("P2_Latch_Set_Logic", "out", "Pump_2_In_Failure", "inA")
    builder.add_link("P2_Reset_Condition", "out", "Pump_2_In_Failure", "inB")

    # 4. REVISED: Wire the Final Command Logic with Failover
    # P1 Command Logic: Run P1 if it's lead and not failed, OR if P2 is lead and IS failed.
    builder.add_link(
        "P1_Lead_Cmd_Request", "out", "Normal_Run_Cmd_P1", "inA"
    )  # P1 Lead selected
    builder.add_not("Pump_1_In_Failure_Not")
    builder.add_link("Pump_1_In_Failure", "out", "Pump_1_In_Failure_Not", "in")
    builder.add_link(
        "Pump_1_In_Failure_Not", "out", "Normal_Run_Cmd_P1", "inB"
    )  # and P1 not failed

    builder.add_link(
        "P2_Lead_Cmd_Request", "out", "Failover_Run_Cmd_P1", "inA"
    )  # P2 Lead selected
    builder.add_link(
        "Pump_2_In_Failure", "out", "Failover_Run_Cmd_P1", "inB"
    )  # and P2 IS failed

    builder.add_link("Normal_Run_Cmd_P1", "out", "Final_Cmd_Logic_P1", "inA")
    builder.add_link("Failover_Run_Cmd_P1", "out", "Final_Cmd_Logic_P1", "inB")
    builder.add_link("Final_Cmd_Logic_P1", "out", "Pump_1_Cmd", "in16")

    # P2 Command Logic: Run P2 if it's lead and not failed, OR if P1 is lead and IS failed.
    builder.add_link(
        "P2_Lead_Cmd_Request", "out", "Normal_Run_Cmd_P2", "inA"
    )  # P2 Lead selected
    builder.add_not("Pump_2_In_Failure_Not")
    builder.add_link("Pump_2_In_Failure", "out", "Pump_2_In_Failure_Not", "in")
    builder.add_link(
        "Pump_2_In_Failure_Not", "out", "Normal_Run_Cmd_P2", "inB"
    )  # and P2 not failed

    builder.add_link(
        "P1_Lead_Cmd_Request", "out", "Failover_Run_Cmd_P2", "inA"
    )  # P1 Lead selected
    builder.add_link(
        "Pump_1_In_Failure", "out", "Failover_Run_Cmd_P2", "inB"
    )  # and P1 IS failed

    builder.add_link("Normal_Run_Cmd_P2", "out", "Final_Cmd_Logic_P2", "inA")
    builder.add_link("Failover_Run_Cmd_P2", "out", "Final_Cmd_Logic_P2", "inB")
    builder.add_link("Final_Cmd_Logic_P2", "out", "Pump_2_Cmd", "in16")

    # 5. Wire the Final Alarms
    builder.add_link("Pump_1_In_Failure", "out", "Pump_1_Failure_Alarm", "in16")
    builder.add_link("Pump_2_In_Failure", "out", "Pump_2_Failure_Alarm", "in16")

    # --- Save the .bog file ---
    bog_filename = "generic_pump_rotator.bog"
    output_path = os.path.join(args.output_dir, bog_filename)
    os.makedirs(args.output_dir, exist_ok=True)
    builder.save(output_path)
    print(
        f"\nSuccessfully created Niagara .bog file at: {os.path.abspath(output_path)}"
    )


if __name__ == "__main__":
    main()
