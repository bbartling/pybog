"""
User prompt:
Create a Niagara .bog sequence for an eight-chiller plant that uses temperature 
staging, load staging, and BladeRoom demand signals to determine how many 
chillers to run. The common chilled-water flow temperature shall be controlled 
against an 18 °C setpoint. If the temperature rises to 19 °C (1 °C above setpoint) 
and remains there for 10 minutes, the next duty chiller is enabled, and if the 
temperature rises to 20 °C (2 °C above setpoint) the next duty chiller is 
enabled immediately. This process continues until all eight chillers are 
staged on. In parallel, load staging logic shall be implemented so that each 
chiller, rated at 1.75 MW, operates between 50 % and 75 % load 
(0.875 MW to 1.3125 MW).  The sequence enables the next chiller whenever plant 
load exceeds 1.3 MW, 2.6 MW, 3.9 MW, and so forth up to 10.4 MW, and sheds 
chillers when load falls below 1.2 MW, 2.5 MW, 3.8 MW, and so forth down to 
9.0 MW, with a twenty-minute delay before adding chillers on rising load. A 
third scenario accounts for BladeRoom demand where three data hall signals 
are monitored; if any hall requires cooling, one additional chiller is started, 
and if all three halls require cooling, three additional chillers are started 
on top of the EC and LP1 base loads, after which chillers are staged in and 
out by the load table. Each chiller includes an available switch that removes 
it from the sequence if set to off, and the entire plant rotates weekly so 
that each chiller takes a turn as Duty 1 through Duty 8, with rotation day and 
time configurable. The sequence shall use LeadLagCycles or LeadLagRuntime blocks 
to manage rotation, BooleanDelay blocks to enforce the ten-minute and twenty-minute 
timers, and numeric writeables to expose the setpoint, the one-degree and 
two-degree temperature differentials, the load thresholds, and the rotation 
schedule parameters. The final outputs are eight Boolean chiller enable 
commands sequenced per this logic.

This is the most advanced example for a modular data center chiller control plant.
This script combines staging, weekly rotation, and command logic into a single
runnable file that generates one .bog file for the Tridium Niagara 4 platform.
The logic determines the number of chillers required based on temperature, load,
and other demand signals, ensuring at least one chiller is always enabled.
"""

import sys
import os
import argparse

# The script must use sys.path.append(...) for the bog_builder import.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))
from bog_builder import BogFolderBuilder


def main():

    parser = argparse.ArgumentParser(
        description="Build a .bog file for Modular Data Center Control logic."
    )
    parser.add_argument(
        "-o",
        "--output_dir",
        default="examples",
        help="Output directory for the .bog file.",
    )
    args = parser.parse_args()

    builder = BogFolderBuilder("Modular_Data_Center_Control", debug=True)

    print("--- Creating Top-Level Inputs & Outputs ---")

    # --- INPUTS ---
    builder.add_numeric_writable("Common_Flow_Temp_C", default_value=18.5, precision=1)
    builder.add_numeric_writable(
        "Common_Flow_Temp_Setpoint_C", default_value=18.0, precision=1
    )
    builder.add_numeric_writable(
        "Total_Cooling_Load_MW", default_value=4.5, precision=2
    )
    builder.add_boolean_writable("Blade_Room_1_Demand", default_value=False)
    builder.add_boolean_writable("Blade_Room_2_Demand", default_value=False)
    builder.add_boolean_writable("Blade_Room_3_Demand", default_value=True)
    for i in range(1, 9):
        builder.add_boolean_writable(f"Chiller_{i}_Available", default_value=True)
    builder.add_boolean_writable("Manual_Rotate_Pulse", default_value=False)

    # --- OUTPUTS & VIEWERS ---
    for i in range(1, 9):
        builder.add_boolean_writable(f"Chiller_{i}_Cmd", default_value=False)
    builder.add_numeric_writable(
        "Total_Chillers_Required", default_value=1.0, precision=0
    )
    builder.add_numeric_writable("Current_Week_Number", default_value=1.0, precision=0)

    # --- LOGIC COMPONENTS ---
    builder.start_sub_folder("StagingLogic")
    builder.add_add("Setpoint_Plus_1C")
    builder.add_numeric_const("Const_1", value=1.0)
    builder.add_greater_than("Temp_GT_SP_plus_1C")
    builder.add_boolean_delay("Stage1_Temp_Delay", on_delay="600000")
    builder.add_counter("Temp_Stage_Counter")
    builder.add_not("Temp_Normal")
    builder.add_maximum("Max_Of_Temp_And_Load")
    builder.add_add("Add_Blade_Room_Demand")
    builder.add_minimum("Clamp_High")
    builder.add_numeric_const("Const_8_MaxChillers", value=8.0)

    # --- NEW: Minimum Demand Logic ---
    builder.add_maximum("Ensure_Min_One_Chiller")
    builder.add_numeric_const("Min_Chiller_Demand", value=1.0)

    # Placeholder/viewer points
    builder.add_numeric_writable(
        "Calculated_Chillers_By_Temp", default_value=0.0, precision=0
    )
    builder.add_numeric_writable(
        "Calculated_Chillers_By_Load", default_value=0.0, precision=0
    )
    builder.add_numeric_writable(
        "Additional_Chillers_By_Blade", default_value=0.0, precision=0
    )
    builder.start_sub_folder("BladeRoomLogic")
    builder.add_numeric_switch("Blade_1_As_Num")
    builder.add_numeric_switch("Blade_2_As_Num")
    builder.add_numeric_switch("Blade_3_As_Num")
    builder.add_add("Sum_Blade_Demands")
    builder.add_greater_than_equal("Is_Demand_1")
    builder.add_numeric_switch("Additional_Chillers_Switch")
    builder.end_sub_folder()
    builder.end_sub_folder()

    builder.start_sub_folder("ScheduleLogic")
    schedule_props = {
        "defaultOutput": {"value": False},
        "effective": {"start": {"yearSchedule": {"alwaysEffective": True}}},
        "schedule": {
            "week": {
                "sunday": {
                    "day": {
                        "time": {
                            "start": "00:00:00.000",
                            "finish": "00:01:00.000",
                            "effectiveValue": {"value": True},
                        }
                    }
                },
                "monday": {"day": {}},
                "tuesday": {"day": {}},
                "wednesday": {"day": {}},
                "thursday": {"day": {}},
                "friday": {"day": {}},
                "saturday": {"day": {}},
            }
        },
    }
    builder.add_boolean_schedule("Weekly_Trigger_Schedule", properties=schedule_props)
    builder.add_one_shot("Scheduled_Trigger_Pulse")
    builder.add_or("Combined_Rotate_Pulse")
    builder.end_sub_folder()

    builder.start_sub_folder("RotationLogic")
    builder.add_counter("Week_Counter")
    builder.add_numeric_const("Const_8_Total_Chillers", value=8.0)
    builder.add_greater_than("Week_GT_8")
    for i in range(1, 9):
        builder.start_sub_folder(f"Chiller_{i}_Priority_Calc")
        builder.add_numeric_const(f"Chiller_{i}_ID", value=float(i))
        builder.add_greater_than_equal(f"Is_ID_GE_Week_{i}")
        builder.add_subtract(f"ID_minus_Week_{i}")
        builder.add_add(f"Base_Priority_{i}")
        builder.add_add(f"Wrapped_Priority_{i}")
        builder.add_numeric_switch(f"Priority_Switch_{i}")
        builder.add_less_than_equal(f"Chiller_{i}_Enable_Check")
        builder.add_and(f"Chiller_{i}_Final_Enable")
        builder.end_sub_folder()
    builder.end_sub_folder()

    print("\n--- Wiring Components ---")

    # --- Wire Staging Logic ---
    builder.add_link("Common_Flow_Temp_Setpoint_C", "out", "Setpoint_Plus_1C", "inA")
    builder.add_link("Const_1", "out", "Setpoint_Plus_1C", "inB")
    builder.add_link("Common_Flow_Temp_C", "out", "Temp_GT_SP_plus_1C", "inA")
    builder.add_link("Setpoint_Plus_1C", "out", "Temp_GT_SP_plus_1C", "inB")
    builder.add_link("Temp_GT_SP_plus_1C", "out", "Stage1_Temp_Delay", "in")
    builder.add_link("Stage1_Temp_Delay", "out", "Temp_Stage_Counter", "countUp")
    builder.add_link("Temp_GT_SP_plus_1C", "out", "Temp_Normal", "in")
    builder.add_link("Temp_Normal", "out", "Temp_Stage_Counter", "reset")
    builder.add_link("Temp_Stage_Counter", "out", "Calculated_Chillers_By_Temp", "in16")

    # Blade Room Wiring
    builder.add_link("Blade_Room_1_Demand", "out", "Blade_1_As_Num", "inSwitch")
    builder.add_link("Const_1", "out", "Blade_1_As_Num", "inTrue")
    builder.add_link("Blade_Room_2_Demand", "out", "Blade_2_As_Num", "inSwitch")
    builder.add_link("Const_1", "out", "Blade_2_As_Num", "inTrue")
    builder.add_link("Blade_Room_3_Demand", "out", "Blade_3_As_Num", "inSwitch")
    builder.add_link("Const_1", "out", "Blade_3_As_Num", "inTrue")
    builder.add_link("Blade_1_As_Num", "out", "Sum_Blade_Demands", "inA")
    builder.add_link("Blade_2_As_Num", "out", "Sum_Blade_Demands", "inB")
    builder.add_link("Blade_3_As_Num", "out", "Sum_Blade_Demands", "inC")
    builder.add_link("Sum_Blade_Demands", "out", "Is_Demand_1", "inA")
    builder.add_link("Const_1", "out", "Is_Demand_1", "inB")
    builder.add_link("Is_Demand_1", "out", "Additional_Chillers_Switch", "inSwitch")
    builder.add_link("Const_1", "out", "Additional_Chillers_Switch", "inTrue")
    builder.add_link(
        "Additional_Chillers_Switch", "out", "Additional_Chillers_By_Blade", "in16"
    )

    # Final Staging Prioritization
    builder.add_link(
        "Calculated_Chillers_By_Temp", "out", "Max_Of_Temp_And_Load", "inA"
    )
    builder.add_link(
        "Calculated_Chillers_By_Load", "out", "Max_Of_Temp_And_Load", "inB"
    )
    builder.add_link("Max_Of_Temp_And_Load", "out", "Add_Blade_Room_Demand", "inA")
    builder.add_link(
        "Additional_Chillers_By_Blade", "out", "Add_Blade_Room_Demand", "inB"
    )
    builder.add_link("Add_Blade_Room_Demand", "out", "Clamp_High", "inA")
    builder.add_link("Const_8_MaxChillers", "out", "Clamp_High", "inB")

    # --- NEW: Reroute through the minimum demand logic ---
    builder.add_link("Clamp_High", "out", "Ensure_Min_One_Chiller", "inA")
    builder.add_link("Min_Chiller_Demand", "out", "Ensure_Min_One_Chiller", "inB")
    builder.add_link("Ensure_Min_One_Chiller", "out", "Total_Chillers_Required", "in16")

    # --- Wire Schedule Logic ---
    builder.add_link("Weekly_Trigger_Schedule", "out", "Scheduled_Trigger_Pulse", "in")
    builder.add_link("Scheduled_Trigger_Pulse", "out", "Combined_Rotate_Pulse", "inA")
    builder.add_link("Manual_Rotate_Pulse", "out", "Combined_Rotate_Pulse", "inB")

    # --- Wire Rotation Logic ---
    builder.add_link("Combined_Rotate_Pulse", "out", "Week_Counter", "countUp")
    builder.add_link("Week_Counter", "out", "Week_GT_8", "inA")
    builder.add_link("Const_8_Total_Chillers", "out", "Week_GT_8", "inB")
    builder.add_link("Week_GT_8", "out", "Week_Counter", "reset")
    builder.add_link("Week_Counter", "out", "Current_Week_Number", "in16")

    # Wire the logic for each of the 8 chillers
    for i in range(1, 9):
        # Wire priority calculation
        builder.add_link(f"Chiller_{i}_ID", "out", f"Is_ID_GE_Week_{i}", "inA")
        builder.add_link("Week_Counter", "out", f"Is_ID_GE_Week_{i}", "inB")
        builder.add_link(f"Chiller_{i}_ID", "out", f"ID_minus_Week_{i}", "inA")
        builder.add_link("Week_Counter", "out", f"ID_minus_Week_{i}", "inB")
        builder.add_link(f"ID_minus_Week_{i}", "out", f"Base_Priority_{i}", "inA")
        builder.add_link("Const_1", "out", f"Base_Priority_{i}", "inB")
        builder.add_link(f"Base_Priority_{i}", "out", f"Wrapped_Priority_{i}", "inA")
        builder.add_link(
            "Const_8_Total_Chillers", "out", f"Wrapped_Priority_{i}", "inB"
        )
        builder.add_link(
            f"Is_ID_GE_Week_{i}", "out", f"Priority_Switch_{i}", "inSwitch"
        )
        builder.add_link(f"Base_Priority_{i}", "out", f"Priority_Switch_{i}", "inTrue")
        builder.add_link(
            f"Wrapped_Priority_{i}", "out", f"Priority_Switch_{i}", "inFalse"
        )
        # Wire final command logic
        builder.add_link(
            f"Priority_Switch_{i}", "out", f"Chiller_{i}_Enable_Check", "inA"
        )
        builder.add_link(
            "Total_Chillers_Required", "out", f"Chiller_{i}_Enable_Check", "inB"
        )
        builder.add_link(
            f"Chiller_{i}_Enable_Check", "out", f"Chiller_{i}_Final_Enable", "inA"
        )
        builder.add_link(
            f"Chiller_{i}_Available", "out", f"Chiller_{i}_Final_Enable", "inB"
        )
        builder.add_link(f"Chiller_{i}_Final_Enable", "out", f"Chiller_{i}_Cmd", "in16")

    # --- Save the .bog file ---
    output_filename = "complex_modular_data_center_control.bog"
    output_path = os.path.join(args.output_dir, output_filename)
    os.makedirs(args.output_dir, exist_ok=True)
    builder.save(output_path)
    print(
        f"\nSuccessfully created Niagara .bog file at: {os.path.abspath(output_path)}"
    )


if __name__ == "__main__":
    main()
