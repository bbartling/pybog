"""
Human asks via Chat input:

Create a Niagara .bog for a simple chiller plant with one air-cooled chiller and two chilled-water pumps.
Expose at the top level: a Boolean output for the chiller start command, two Boolean outputs for Pump A/B
commands, and two Boolean input statuses for Pump A/B. Use a single “Logic” sub-folder for all internal
blocks. Enable the plant from an outside-air temperature input wired into a kitControl Tstat block with
setpoint 60 and a differential of 2; when the Tstat output is true, drive the chiller start Boolean
output true immediately with correct settings on the Tstat direction. Feed that same Tstat boolean output
into a kitControl LeadLagRuntime/Cycles "in" and have the block configured for 2 pumps, with rotation
based on a max runtime of 40 hours, and use Counters to record each pump start. Before each pump command
leaves the Lead/Lag block, insert a kitControl BooleanDelay set to 30 seconds, one delay per pump output,
then wire each delayed signal to its respective Pump A/B command. OR the two pump status inputs and wire
the OR output back to the Lead/Lag feedback input. Keep all algorithm inputs/outputs at top level,
all logic inside the single sub-folder, and arrange the wiresheet cleanly.
"""

import os, argparse
from bog_builder import BogFolderBuilder


def main():
    """
    Builds and saves the simple chiller plant .bog file with refactored configuration links.
    """
    p = argparse.ArgumentParser(
        description="Build a G36 Trim & Respond for duct pressure"
    )
    p.add_argument("-o", "--output_dir", default="examples")
    args = p.parse_args()

    # Initialize the BogFolderBuilder with the top-level folder name.
    builder = BogFolderBuilder("SimpleChillerPlant", debug=True)

    # --- Top-Level Inputs & Outputs ---
    builder.add_numeric_writable("Outside_Air_Temperature", default_value=75.0)
    builder.add_boolean_writable("Pump_A_Status", default_value=False)
    builder.add_boolean_writable("Pump_B_Status", default_value=False)

    builder.add_boolean_writable("Chiller_Start_Cmd", default_value=False)
    builder.add_boolean_writable("Pump_A_Cmd", default_value=False)
    builder.add_boolean_writable("Pump_B_Cmd", default_value=False)

    # --- Logic Components (organized inside a single sub-folder) ---
    builder.start_sub_folder("Logic")

    # --- Tstat Refactoring Start ---
    # 1. Add Tstat component without complex properties.
    builder.add_tstat("Plant_Enable_Tstat")

    # 2. Create explicit constants for Tstat configuration.
    builder.add_numeric_const("Enable_Setpoint", properties={"value": 60.0})
    builder.add_numeric_const("Enable_Differential", properties={"value": 2.0})
    # action=False means direct-acting.
    builder.add_boolean_const(
        "Enable_Action_Direct", properties={"value": False}
    )
    # --- Tstat Refactoring End ---

    # LeadLagCycles block to rotate the two pumps.
    lead_lag_properties = {"numberOutputs": 2, "maxRuntime": "40h"}
    builder.add_lead_lag_cycles("Pump_Rotator", properties=lead_lag_properties)

    # Counters to track the number of starts for each pump.
    builder.add_counter("Pump_A_Start_Counter")
    builder.add_counter("Pump_B_Start_Counter")

    # BooleanDelay blocks to delay the start command to each pump.
    delay_properties = {"onDelay": "30000"}
    builder.add_boolean_delay(
        "Pump_A_Start_Delay", on_delay=delay_properties["onDelay"]
    )
    builder.add_boolean_delay(
        "Pump_B_Start_Delay", on_delay=delay_properties["onDelay"]
    )

    # OR gate to combine pump status signals for feedback.
    builder.add_or("Pump_Feedback_Or")

    builder.end_sub_folder()

    # --- Wiring ---
    # 1. Wire the plant enable logic.
    builder.add_link("Outside_Air_Temperature", "out", "Plant_Enable_Tstat", "cv")

    # --- Tstat Refactoring Links ---
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
    # --- End Tstat Refactoring Links ---

    # The Tstat output enables both the chiller and the pump rotator.
    builder.add_link("Plant_Enable_Tstat", "out", "Chiller_Start_Cmd", "in16")
    builder.add_link("Plant_Enable_Tstat", "out", "Pump_Rotator", "in")

    # 2. Wire the pump command chain: LeadLag -> Delay -> Final Command.
    builder.add_link("Pump_Rotator", "outA", "Pump_A_Start_Delay", "in")
    builder.add_link("Pump_Rotator", "outB", "Pump_B_Start_Delay", "in")

    builder.add_link("Pump_A_Start_Delay", "out", "Pump_A_Cmd", "in16")
    builder.add_link("Pump_B_Start_Delay", "out", "Pump_B_Cmd", "in16")

    # 3. Wire the pump start counters. The final command triggers the count.
    builder.add_link("Pump_A_Cmd", "out", "Pump_A_Start_Counter", "countUp")
    builder.add_link("Pump_B_Cmd", "out", "Pump_B_Start_Counter", "countUp")

    # 4. Wire the counter outputs back to the LeadLag block for rotation logic.
    # Note: The builder automatically handles StatusNumericToNumber conversion here.
    builder.add_link("Pump_A_Start_Counter", "out", "Pump_Rotator", "cycleCountA")
    builder.add_link("Pump_B_Start_Counter", "out", "Pump_Rotator", "cycleCountB")

    # 5. Wire the pump status feedback logic.
    builder.add_link("Pump_A_Status", "out", "Pump_Feedback_Or", "inA")
    builder.add_link("Pump_B_Status", "out", "Pump_Feedback_Or", "inB")
    builder.add_link("Pump_Feedback_Or", "out", "Pump_Rotator", "feedback")

    # --- Save the .bog file ---
    os.makedirs(args.output_dir, exist_ok=True)
    out = os.path.join(args.output_dir, "simple_chiller_plant.bog")
    builder.save(out)
    print(f"Created {out}")


if __name__ == "__main__":
    main()
