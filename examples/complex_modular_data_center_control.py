import sys
import os

# The script must use sys.path.append(...) for the bog_builder import. [cite: 7]
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))
from bog_builder import BogFolderBuilder


def main():
    """
    Builds a complete, modular data center chiller control logic file.
    This script combines staging, weekly rotation, and command logic into a single
    runnable file that generates one .bog file for the Tridium Niagara 4 platform.
    The logic determines the number of chillers required based on temperature, load,
    and other demand signals. It then rotates the available chillers on a weekly
    basis to ensure even wear and commands the appropriate lead units.
    """
    # Initialize the builder with a descriptive name for the top-level folder. [cite: 11]
    builder = BogFolderBuilder("Modular_Data_Center_Control", debug=True)

    print("--- Creating Top-Level Inputs & Outputs ---")

    # --- INPUTS ---
    # Staging Inputs (from sensors and setpoints)
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

    # Rotation/Availability Inputs
    for i in range(1, 9):
        builder.add_boolean_writable(f"Chiller_{i}_Available", default_value=True)
    builder.add_boolean_writable("Manual_Rotate_Pulse", default_value=False)

    # --- OUTPUTS & VIEWERS ---
    # Final commands to physical equipment
    for i in range(1, 9):
        builder.add_boolean_writable(f"Chiller_{i}_Cmd", default_value=False)

    # Viewers for intermediate logic values
    builder.add_numeric_writable(
        "Total_Chillers_Required", default_value=0.0, precision=0
    )
    builder.add_numeric_writable("Current_Week_Number", default_value=1.0, precision=0)

    # --- LOGIC COMPONENTS ---
    # Use sub-folders to organize complex logic. [cite: 9]

    # 1. Staging Logic: Determines how many chillers are needed.
    builder.start_sub_folder("StagingLogic")
    builder.add_add("Setpoint_Plus_1C")
    builder.add_numeric_const("Const_1", value=1.0)
    builder.add_greater_than("Temp_GT_SP_plus_1C")
    builder.add_boolean_delay(
        "Stage1_Temp_Delay", on_delay="600000"
    )  # 10 minutes [cite: 22]
    builder.add_counter("Temp_Stage_Counter")
    builder.add_not("Temp_Normal")

    builder.add_maximum("Max_Of_Temp_And_Load")
    builder.add_add("Add_Blade_Room_Demand")
    builder.add_minimum("Clamp_High")
    builder.add_numeric_const("Const_8_MaxChillers", value=8.0)

    # Placeholder/viewer points inside staging logic
    builder.add_numeric_writable(
        "Calculated_Chillers_By_Temp", default_value=0.0, precision=0
    )
    builder.add_numeric_writable(
        "Calculated_Chillers_By_Load", default_value=0.0, precision=0
    )  # Note: Load logic is not fully built out in source
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
    builder.end_sub_folder()  # BladeRoomLogic
    builder.end_sub_folder()  # StagingLogic

    # 2. Schedule Logic: Creates a weekly pulse for rotation.
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
    builder.end_sub_folder()  # ScheduleLogic

    # 3. Rotation Logic: Takes the required number of chillers and rotates them.
    builder.start_sub_folder("RotationLogic")
    builder.add_counter("Week_Counter")
    builder.add_numeric_const("Const_8_Total_Chillers", value=8.0)
    builder.add_greater_than("Week_GT_8")

    # Create Priority Calculation Logic for each Chiller
    for i in range(1, 9):
        builder.start_sub_folder(f"Chiller_{i}_Priority_Calc")
        # Priority = if ID >= Week then (ID-Week)+1 else (ID-Week)+1+8
        builder.add_numeric_const(f"Chiller_{i}_ID", value=float(i))
        builder.add_greater_than_equal(f"Is_ID_GE_Week_{i}")
        builder.add_subtract(f"ID_minus_Week_{i}")
        builder.add_add(f"Base_Priority_{i}")
        builder.add_add(f"Wrapped_Priority_{i}")
        builder.add_numeric_switch(f"Priority_Switch_{i}")
        builder.add_less_than_equal(f"Chiller_{i}_Enable_Check")
        builder.add_and(f"Chiller_{i}_Final_Enable")
        builder.end_sub_folder()  # Chiller_i_Priority_Calc
    builder.end_sub_folder()  # RotationLogic

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
    builder.add_link(
        "Clamp_High", "out", "Total_Chillers_Required", "in16"
    )  # Link to top-level viewer

    # --- Wire Schedule Logic ---
    builder.add_link("Weekly_Trigger_Schedule", "out", "Scheduled_Trigger_Pulse", "in")
    builder.add_link("Scheduled_Trigger_Pulse", "out", "Combined_Rotate_Pulse", "inA")
    builder.add_link("Manual_Rotate_Pulse", "out", "Combined_Rotate_Pulse", "inB")

    # --- Wire Rotation Logic ---
    builder.add_link("Combined_Rotate_Pulse", "out", "Week_Counter", "countUp")
    builder.add_link("Week_Counter", "out", "Week_GT_8", "inA")
    builder.add_link("Const_8_Total_Chillers", "out", "Week_GT_8", "inB")
    builder.add_link("Week_GT_8", "out", "Week_Counter", "reset")
    builder.add_link(
        "Week_Counter", "out", "Current_Week_Number", "in16"
    )  # Link to top-level viewer

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
    # The output filename must be hardcoded as a string. [cite: 6]
    output_filename = "modular_data_center_combined_logic.bog"
    builder.save(output_filename)
    print(f"\nSuccessfully created Niagara .bog file: {output_filename}")


if __name__ == "__main__":
    # The script must not accept any command-line arguments. [cite: 8]
    main()
