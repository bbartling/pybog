"""
Creates a Niagara .bog for a simple chiller plant with one air-cooled chiller and two chilled-water pumps.
The logic enables the plant based on outside air temperature and rotates the pumps based on cycle count.
"""

import os, argparse
from bog_builder import BogFolderBuilder


def main():
    """
    Builds and saves the simple chiller plant .bog file with refactored configuration links.
    """
    p = argparse.ArgumentParser(
        description="Build a .bog file for a simple one-chiller, two-pump plant."
    )
    p.add_argument("-o", "--output_dir", default="examples")
    args = p.parse_args()

    # Initialize the BogFolderBuilder with the top-level folder name.
    builder = BogFolderBuilder("SimpleChillerPlant", debug=True)

    print("--- Creating Top-Level Inputs & Outputs ---")
    # --- Top-Level Inputs & Outputs ---
    builder.add_numeric_writable("Outside_Air_Temperature", default_value=75.0)
    builder.add_boolean_writable("Pump_A_Status", default_value=False)
    builder.add_boolean_writable("Pump_B_Status", default_value=False)

    builder.add_boolean_writable("Chiller_Start_Cmd", default_value=False)
    builder.add_boolean_writable("Pump_A_Cmd", default_value=False)
    builder.add_boolean_writable("Pump_B_Cmd", default_value=False)

    print("\n--- Creating Logic Components inside 'Logic' sub-folder ---")
    # --- Logic Components (organized inside a single sub-folder) ---
    builder.start_sub_folder("Logic")

    # Tstat block to enable the plant based on OAT.
    builder.add_tstat("Plant_Enable_Tstat")
    builder.add_numeric_const("Enable_Setpoint", value=60.0)
    builder.add_numeric_const("Enable_Differential", value=2.0)
    # action=False means direct-acting (output is true when CV > SP).
    builder.add_boolean_const("Enable_Action_Direct", value=True)

    # LeadLagCycles block to rotate the two pumps.
    lead_lag_properties = {"numberOutputs": 2, "maxRuntime": "40h"}
    builder.add_lead_lag_cycles("Pump_Rotator", properties=lead_lag_properties)

    # Counters to track the number of starts for each pump.
    builder.add_counter("Pump_A_Start_Counter")
    builder.add_counter("Pump_B_Start_Counter")

    # BooleanDelay blocks to delay the start command to each pump.
    builder.add_boolean_delay("Pump_A_Start_Delay", on_delay="30000")  # 30 seconds
    builder.add_boolean_delay("Pump_B_Start_Delay", on_delay="30000")  # 30 seconds

    # OR gate to combine pump status signals for feedback.
    builder.add_or("Pump_Feedback_Or")

    builder.end_sub_folder()

    print("\n--- Wiring Components ---")
    # --- Wiring ---
    # 1. Wire the plant enable logic.
    builder.add_link("Outside_Air_Temperature", "out", "Plant_Enable_Tstat", "cv")
    builder.add_link("Enable_Setpoint", "out", "Plant_Enable_Tstat", "sp")
    builder.add_link("Enable_Differential", "out", "Plant_Enable_Tstat", "diff")
    # Apply the necessary conversion for the action slot.
    builder.add_link(
        "Enable_Action_Direct",
        "out",
        "Plant_Enable_Tstat",
        "action",
        link_type="b:ConversionLink",
        converter_type="conv:StatusBooleanToFrozenEnum",
    )

    # 2. The Tstat output enables both the chiller and the pump rotator.
    builder.add_link("Plant_Enable_Tstat", "out", "Chiller_Start_Cmd", "in16")
    builder.add_link("Plant_Enable_Tstat", "out", "Pump_Rotator", "in")

    # 3. Wire the pump command chain: LeadLag -> Delay -> Final Command.
    builder.add_link("Pump_Rotator", "outA", "Pump_A_Start_Delay", "in")
    builder.add_link("Pump_Rotator", "outB", "Pump_B_Start_Delay", "in")

    builder.add_link("Pump_A_Start_Delay", "out", "Pump_A_Cmd", "in16")
    builder.add_link("Pump_B_Start_Delay", "out", "Pump_B_Cmd", "in16")

    # 4. Wire the pump start counters. The final command triggers the count.
    builder.add_link("Pump_A_Cmd", "out", "Pump_A_Start_Counter", "countUp")
    builder.add_link("Pump_B_Cmd", "out", "Pump_B_Start_Counter", "countUp")

    # 5. Wire the counter outputs back to the LeadLag block for rotation logic.
    builder.add_link("Pump_A_Start_Counter", "out", "Pump_Rotator", "cycleCountA")
    builder.add_link("Pump_B_Start_Counter", "out", "Pump_Rotator", "cycleCountB")

    # 6. Wire the pump status feedback logic.
    builder.add_link("Pump_A_Status", "out", "Pump_Feedback_Or", "inA")
    builder.add_link("Pump_B_Status", "out", "Pump_Feedback_Or", "inB")
    builder.add_link("Pump_Feedback_Or", "out", "Pump_Rotator", "feedback")

    # --- Save the .bog file ---
    bog_filename = "hvac_simple_chiller_plant_one.bog"
    output_path = os.path.join(args.output_dir, bog_filename)
    os.makedirs(args.output_dir, exist_ok=True)
    builder.save(output_path)
    print(
        f"\nSuccessfully created Niagara .bog file at: {os.path.abspath(output_path)}"
    )


if __name__ == "__main__":
    main()
