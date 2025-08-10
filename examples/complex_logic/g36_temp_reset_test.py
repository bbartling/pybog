import sys
import os
import argparse

# Add the 'src' directory to the Python path to find the builder
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.bog_builder_new import BogFolderBuilder


def main():
    """
    This script builds a simple test case to demonstrate time-delayed logic
    and a setpoint reset, which are core concepts for Guideline 36
    "Trim and Respond" sequences.

    Logic:
    1. Compares a Zone Temperature to a Setpoint.
    2. If the temperature is too high, a 10-second timer starts.
    3. If the condition remains true for the full 10 seconds, a 'Reset'
       block is triggered to adjust a Supply Air Temperature (SAT) Setpoint.
    """
    parser = argparse.ArgumentParser(
        description="Build a .bog file to test time-delayed reset logic."
    )
    parser.add_argument(
        "-o", "--output_dir", default="examples", help="Output directory for the .bog file."
    )
    args = parser.parse_args()

    script_filename = os.path.basename(__file__).replace(".py", "")

    builder = BogFolderBuilder("Guideline36_Reset_Test")

    print("Creating top-level inputs and outputs...")

    # --- Inputs ---
    builder.add_numeric_writable("Zone_Temp", default_value=75.0)
    builder.add_numeric_writable("Zone_Setpoint", default_value=72.0)
    builder.add_numeric_writable("Initial_SAT_Setpoint", default_value=55.0)
    builder.add_numeric_writable("Reset_Amount", default_value=-0.5)
    builder.add_boolean_writable("Enable_Logic", default_value=True)

    # --- Outputs ---
    builder.add_numeric_writable("Active_SAT_Setpoint")
    builder.add_boolean_writable("Condition_Sustained")

    print("Creating logic components inside 'TrimRespondLogic' folder...")
    builder.start_sub_folder("TrimRespondLogic")

    builder.add_component("kitControl:GreaterThan", "Temp_Exceeded_Check")

    builder.add_component(
        "kitControl:BooleanDelay",
        "Condition_Sustained_Timer",
        properties={"onDelay": "10s"}
    )

    builder.add_component("kitControl:And", "Enable_And_Gate")

    builder.add_component("kitControl:Reset", "SAT_Reset_Block")

    builder.add_numeric_switch("Setpoint_Selector")

    builder.end_sub_folder()

    print("Wiring components...")

    builder.add_link("Zone_Temp", "out", "Temp_Exceeded_Check", "inA")
    builder.add_link("Zone_Setpoint", "out", "Temp_Exceeded_Check", "inB")

    builder.add_link("Temp_Exceeded_Check", "out", "Condition_Sustained_Timer", "in")

    builder.add_link("Condition_Sustained_Timer", "out", "Enable_And_Gate", "inA")
    builder.add_link("Enable_Logic", "out", "Enable_And_Gate", "inB")

    builder.add_link("Enable_And_Gate", "out", "SAT_Reset_Block", "increment")
    
    builder.add_link("Initial_SAT_Setpoint", "out", "SAT_Reset_Block", "in")
    builder.add_link("Reset_Amount", "out", "SAT_Reset_Block", "incrementValue")

    builder.add_link("Enable_And_Gate", "out", "Setpoint_Selector", "inSwitch")
    builder.add_link("SAT_Reset_Block", "out", "Setpoint_Selector", "inTrue")
    builder.add_link("Initial_SAT_Setpoint", "out", "Setpoint_Selector", "inFalse")

    # --- Final Outputs ---
    builder.add_link("Setpoint_Selector", "out", "Active_SAT_Setpoint", "in16")
    builder.add_link("Condition_Sustained_Timer", "out", "Condition_Sustained", "in16")

    bog_filename = f"{script_filename}.bog"
    output_path = os.path.join(args.output_dir, bog_filename)
    os.makedirs(args.output_dir, exist_ok=True)
    builder.save(output_path)
    print(f"\nSuccessfully created Niagara .bog file at: {output_path}")
    print("You can now test this file in Niagara Workbench to see the time-delayed reset in action.")


if __name__ == "__main__":
    main()
