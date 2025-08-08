import sys
import os
import argparse

# Add the 'src' directory to the Python path to find the builder
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.bog_builder_new import BogFolderBuilder


def main():
    """
    Program for a VAV box only to count requests for pressure.
    """
    parser = argparse.ArgumentParser(
        description="Build a .bog file to test time-delayed reset logic."
    )
    parser.add_argument(
        "-o", "--output_dir", default="examples", help="Output directory for the .bog file."
    )
    args = parser.parse_args()

    script_filename = os.path.basename(__file__).replace(".py", "")

    # 1. Initialize the builder
    builder = BogFolderBuilder("Guideline36_Reset_Test")

    # 2. Create all the top-level components for user interaction.
    print("Creating top-level inputs and outputs...")

    # --- Inputs ---
    builder.add_numeric_writable("Zone_Temp", default_value=75.0)
    builder.add_numeric_writable("Zone_Setpoint", default_value=72.0)
    builder.add_numeric_writable("Initial_SAT_Setpoint", default_value=55.0)
    builder.add_numeric_writable("Reset_Amount", default_value=-0.5) # Negative to cool down
    builder.add_boolean_writable("Enable_Logic", default_value=True)

    # --- Outputs ---
    builder.add_numeric_writable("Active_SAT_Setpoint")
    builder.add_boolean_writable("Condition_Sustained") # To see when the timer completes

    # 3. Encapsulate the core logic in a sub-folder for organization.
    print("Creating logic components inside 'TrimRespondLogic' folder...")
    builder.start_sub_folder("TrimRespondLogic")

    # --- Logic Blocks ---
    # Compares the zone temp to its setpoint.
    builder.add_component("kitControl:GreaterThan", "Temp_Exceeded_Check")

    # Delays the boolean signal. It will only turn true if the input
    # has been true for the full 'onDelay' time (10 seconds).
    # The properties are set to define the time duration.
    builder.add_component(
        "kitControl:BooleanDelay",
        "Condition_Sustained_Timer",
        properties={"onDelay": "10s"}
    )

    # Ensures the logic only runs when enabled AND the temp condition is met.
    builder.add_component("kitControl:And", "Enable_And_Gate")

    # The Reset block adjusts the setpoint.
    builder.add_component("kitControl:Reset", "SAT_Reset_Block")

    # A switch to select either the initial or the newly reset setpoint.
    builder.add_numeric_switch("Setpoint_Selector")

    builder.end_sub_folder()


    # 4. Register all links to define the data flow.
    print("Wiring components...")

    # --- Inside the sub-folder ---
    # Link the main inputs to the first logic block.
    builder.add_link("Zone_Temp", "out", "Temp_Exceeded_Check", "inA")
    builder.add_link("Zone_Setpoint", "out", "Temp_Exceeded_Check", "inB")

    # Link the comparison result to the timer.
    builder.add_link("Temp_Exceeded_Check", "out", "Condition_Sustained_Timer", "in")

    # Link the timer output and the master enable switch to the AND gate.
    builder.add_link("Condition_Sustained_Timer", "out", "Enable_And_Gate", "inA")
    builder.add_link("Enable_Logic", "out", "Enable_And_Gate", "inB")

    # Link the output of the AND gate to the 'increment' action of the Reset block.
    # This will cause the reset to happen when the condition is sustained.
    builder.add_link("Enable_And_Gate", "out", "SAT_Reset_Block", "increment")
    
    # Provide the values for the Reset block.
    builder.add_link("Initial_SAT_Setpoint", "out", "SAT_Reset_Block", "in")
    builder.add_link("Reset_Amount", "out", "SAT_Reset_Block", "incrementValue")

    # Use the output of the AND gate to control the final selector switch.
    builder.add_link("Enable_And_Gate", "out", "Setpoint_Selector", "inSwitch")
    builder.add_link("SAT_Reset_Block", "out", "Setpoint_Selector", "inTrue") # Use reset value if true
    builder.add_link("Initial_SAT_Setpoint", "out", "Setpoint_Selector", "inFalse") # Use initial value if false

    # --- Final Outputs ---
    # Link the internal logic results to the top-level outputs for visibility.
    builder.add_link("Setpoint_Selector", "out", "Active_SAT_Setpoint", "in16")
    builder.add_link("Condition_Sustained_Timer", "out", "Condition_Sustained", "in16")


    # 5. Save the file.
    bog_filename = f"{script_filename}.bog"
    output_path = os.path.join(args.output_dir, bog_filename)
    os.makedirs(args.output_dir, exist_ok=True)
    builder.save(output_path)
    print(f"\nSuccessfully created Niagara .bog file at: {output_path}")
    print("You can now test this file in Niagara Workbench to see the time-delayed reset in action.")


if __name__ == "__main__":
    main()
