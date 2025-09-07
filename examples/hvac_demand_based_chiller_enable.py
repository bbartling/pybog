"""
Demand Based Chiller Enable with Hysteresis
---------------------------------------------
This script builds a wiresheet for a chiller enable/disable sequence driven
by the maximum cooling demand across 10 AHUs. This version replaces the
BooleanLatch with a more direct and stable custom hysteresis logic,
providing a clear Set/Reset (SR) latch behavior.

Algorithm:
- A series of chained 'Maximum' blocks finds the highest cooling valve
  position from 10 AHU inputs.
- An SR latch is constructed using basic logic gates to create a
  'Raw_Chiller_Request'. The request is SET (turned ON) when the max valve
  exceeds 30% and is RESET (turned OFF) only when it falls below 15%.
  This creates the desired hysteresis.
- This raw request signal is then passed through a 'BooleanDelay' block to
  prevent short cycling of the equipment.
- A 30-minute off-delay (1,800,000 ms) keeps the chiller running for a minimum
  period before it can be shut down.
- The final, time-delayed output drives the 'Chiller_Enable_Command'.
"""

import os
import argparse
import sys

# Per instructions, append to sys.path to find bog_builder
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))
from bog_builder import BogFolderBuilder


def main():
    """
    Main function to build and save the chiller enable logic.
    """
    parser = argparse.ArgumentParser(
        description="Build a .bog file for chiller enable logic with custom hysteresis."
    )
    parser.add_argument(
        "-o",
        "--output_dir",
        default="examples",
        help="Output directory for the .bog file.",
    )
    args = parser.parse_args()

    builder = BogFolderBuilder("ChillerEnableWithHysteresis", debug=True)

    print("--- Creating Top-Level I/O Components ---")

    # --- Inputs & Outputs ---
    for i in range(1, 11):
        name = f"AHU_{i:02d}_Cooling_Valve"
        builder.add_numeric_writable(name, default_value=float(0))

    builder.add_boolean_writable("Chiller_Enable_Command", default_value=False)
    builder.add_numeric_writable("Max_Cooling_Valve")

    # --- Logic Components (organized inside a sub-folder) ---
    print("\n--- Creating Logic Components inside 'Logic' sub-folder ---")
    builder.start_sub_folder("Logic")

    # --- Manual Maximum Calculation ---
    builder.add_maximum("Max1")
    builder.add_maximum("Max2")
    builder.add_maximum("Max3")
    builder.add_maximum("Max_Final")

    # --- Hysteresis (SR Latch) Logic ---
    builder.add_numeric_const(
        "Enable_Setpoint", properties={"value": 30.0}
    )
    builder.add_numeric_const(
        "Disable_Setpoint", properties={"value": 15.0}
    )
    builder.add_greater_than("Set_Condition")
    builder.add_less_than("Reset_Condition_Raw")
    builder.add_not("Reset_Condition")
    builder.add_or("Latch_Set_Logic")
    builder.add_and("Raw_Chiller_Request")

    # --- Anti-Short-Cycle Delay ---
    builder.add_boolean_delay("Anti_Short_Cycle_Delay")
    builder.add_numeric_const(
        "Off_Delay_Constant", properties={"value": 1800000.0}
    )  # 30 minutes

    builder.end_sub_folder()

    print("\n--- Wiring Components ---")

    # --- Wire Manual Maximum Calculation ---
    builder.add_link("AHU_01_Cooling_Valve", "out", "Max1", "inA")
    builder.add_link("AHU_02_Cooling_Valve", "out", "Max1", "inB")
    builder.add_link("AHU_03_Cooling_Valve", "out", "Max1", "inC")
    builder.add_link("AHU_04_Cooling_Valve", "out", "Max1", "inD")

    builder.add_link("AHU_05_Cooling_Valve", "out", "Max2", "inA")
    builder.add_link("AHU_06_Cooling_Valve", "out", "Max2", "inB")
    builder.add_link("AHU_07_Cooling_Valve", "out", "Max2", "inC")
    builder.add_link("AHU_08_Cooling_Valve", "out", "Max2", "inD")

    builder.add_link("AHU_09_Cooling_Valve", "out", "Max3", "inA")
    builder.add_link("AHU_10_Cooling_Valve", "out", "Max3", "inB")

    builder.add_link("Max1", "out", "Max_Final", "inA")
    builder.add_link("Max2", "out", "Max_Final", "inB")
    builder.add_link("Max3", "out", "Max_Final", "inC")
    builder.add_link("Max_Final", "out", "Max_Cooling_Valve", "in16")

    # --- Wire Hysteresis (SR Latch) Logic ---
    # Set condition: Max_Cooling_Valve > 30
    builder.add_link("Max_Cooling_Valve", "out", "Set_Condition", "inA")
    builder.add_link("Enable_Setpoint", "out", "Set_Condition", "inB")

    # Reset condition: Max_Cooling_Valve < 15
    builder.add_link("Max_Cooling_Valve", "out", "Reset_Condition_Raw", "inA")
    builder.add_link("Disable_Setpoint", "out", "Reset_Condition_Raw", "inB")
    builder.add_link("Reset_Condition_Raw", "out", "Reset_Condition", "in")

    # Latch logic: Output = (Set OR Output) AND (NOT Reset)
    builder.add_link("Set_Condition", "out", "Latch_Set_Logic", "inA")
    builder.add_link(
        "Raw_Chiller_Request", "out", "Latch_Set_Logic", "inB"
    )  # Feedback loop
    builder.add_link("Latch_Set_Logic", "out", "Raw_Chiller_Request", "inA")
    builder.add_link("Reset_Condition", "out", "Raw_Chiller_Request", "inB")

    # --- Wire Final Command Logic with Delay ---
    builder.add_link("Raw_Chiller_Request", "out", "Anti_Short_Cycle_Delay", "in")

    builder.add_link(
        "Off_Delay_Constant",
        "out",
        "Anti_Short_Cycle_Delay",
        "offDelay",
        link_type="b:ConversionLink",
        converter_type="conv:StatusNumericToRelTime",
    )

    builder.add_link("Anti_Short_Cycle_Delay", "out", "Chiller_Enable_Command", "in16")

    # --- Save the .bog file ---
    bog_filename = "demand_based_chiller_enable_hysteresis.bog"
    output_path = os.path.join(args.output_dir, bog_filename)
    os.makedirs(args.output_dir, exist_ok=True)
    builder.save(output_path)

    print(
        f"\nSuccessfully created Niagara .bog file at: {os.path.abspath(output_path)}"
    )
    print("Drag this file into Niagara Workbench to test the logic.")


if __name__ == "__main__":
    main()
