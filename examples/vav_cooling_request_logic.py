import sys
import os
import argparse

# Add the 'src' directory to the Python path to find the builder
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.bog_builder_new import BogFolderBuilder


def main():
    """
    This script programmatically builds the VAV Box Cooling Request logic
    from ASHRAE Guideline 36, §5.6.8.1.

    It uses a parallel structure with a final Maximum block to prioritize
    requests based on zone temperature deviation and cooling demand.
    """
    parser = argparse.ArgumentParser(
        description="Build a .bog file for VAV Cooling Request logic."
    )
    parser.add_argument(
        "-o", "--output_dir", default="examples", help="Output directory for the .bog file."
    )
    args = parser.parse_args()

    script_filename = os.path.basename(__file__).replace(".py", "")

    # 1. Initialize the builder
    builder = BogFolderBuilder("G36_VAV_Cooling_Req")

    # 2. Create all the top-level components for user interaction.
    print("Creating top-level inputs and outputs...")

    # --- Inputs ---
    builder.add_numeric_writable("ZoneTemp", default_value=78.0)
    builder.add_numeric_writable("ZoneCoolingSpt", default_value=72.0)
    builder.add_numeric_writable("ZoneDemand", default_value=96.0) # Represents the cooling loop command

    # --- Outputs ---
    builder.add_numeric_writable("VAVCoolingRequestsTotal")


    # 3. Build the logic, encapsulating each part in its own sub-folder.
    print("Creating and organizing logic components in sub-folders...")

    # --- Sub-Folder for Setpoint Deviation Calculations ---
    builder.start_sub_folder("SetpointDeviationCalcs")
    builder.add_component("kitControl:Add", "Setpoint_Plus_5F")
    builder.add_component("kitControl:Add", "Setpoint_Plus_3F")
    builder.add_component("kitControl:NumericConst", "Const_5", properties={"out": 5.0})
    builder.add_component("kitControl:NumericConst", "Const_3", properties={"out": 3.0})
    builder.end_sub_folder()

    # --- Sub-Folder for 3 Requests Logic (Temp > SP + 5F) ---
    builder.start_sub_folder("Generate3RequestsLogic")
    builder.add_component("kitControl:GreaterThan", "Temp_GT_SP_plus_5F")
    builder.add_component("kitControl:BooleanDelay", "Timer_2min_Delay3", properties={"onDelay": "120000"}) # 2 minutes
    builder.add_numeric_switch("NumericSwitch_3_Req")
    builder.add_component("kitControl:NumericConst", "Const_3_Req", properties={"out": 3.0})
    builder.end_sub_folder()
    
    # --- Sub-Folder for 2 Requests Logic (Temp > SP + 3F) ---
    builder.start_sub_folder("Generate2RequestsLogic")
    builder.add_component("kitControl:GreaterThan", "Temp_GT_SP_plus_3F")
    builder.add_component("kitControl:BooleanDelay", "Timer_2min_Delay2", properties={"onDelay": "120000"}) # 2 minutes
    builder.add_numeric_switch("NumericSwitch_2_Req")
    builder.add_component("kitControl:NumericConst", "Const_2_Req", properties={"out": 2.0})
    builder.end_sub_folder()

    # --- Sub-Folder for 1 Request Logic (ZoneDemand > 95%) ---
    builder.start_sub_folder("Generate1RequestLogic")
    builder.add_component("kitControl:GreaterThan", "Demand_GT_95")
    builder.add_numeric_switch("NumericSwitch_1_Req")
    builder.add_component("kitControl:NumericConst", "Const_95", properties={"out": 95.0})
    builder.add_component("kitControl:NumericConst", "Const_1_Req", properties={"out": 1.0})
    builder.end_sub_folder()

    # --- Sub-Folder for Final Prioritization ---
    builder.start_sub_folder("Prioritization")
    builder.add_component("kitControl:Maximum", "Maximum")
    builder.end_sub_folder()


    # 4. Register all links to define the data flow.
    print("Wiring components across all folders...")

    # --- Wire Setpoint Deviation Calculations ---
    builder.add_link("ZoneCoolingSpt", "out", "Setpoint_Plus_5F", "inA")
    builder.add_link("Const_5", "out", "Setpoint_Plus_5F", "inB")
    builder.add_link("ZoneCoolingSpt", "out", "Setpoint_Plus_3F", "inA")
    builder.add_link("Const_3", "out", "Setpoint_Plus_3F", "inB")

    # --- Wire Logic for 3 Requests ---
    builder.add_link("ZoneTemp", "out", "Temp_GT_SP_plus_5F", "inA")
    builder.add_link("Setpoint_Plus_5F", "out", "Temp_GT_SP_plus_5F", "inB")
    builder.add_link("Temp_GT_SP_plus_5F", "out", "Timer_2min_Delay3", "in")
    builder.add_link("Timer_2min_Delay3", "out", "NumericSwitch_3_Req", "inSwitch")
    builder.add_link("Const_3_Req", "out", "NumericSwitch_3_Req", "inTrue")

    # --- Wire Logic for 2 Requests ---
    builder.add_link("ZoneTemp", "out", "Temp_GT_SP_plus_3F", "inA")
    builder.add_link("Setpoint_Plus_3F", "out", "Temp_GT_SP_plus_3F", "inB")
    builder.add_link("Temp_GT_SP_plus_3F", "out", "Timer_2min_Delay2", "in")
    builder.add_link("Timer_2min_Delay2", "out", "NumericSwitch_2_Req", "inSwitch")
    builder.add_link("Const_2_Req", "out", "NumericSwitch_2_Req", "inTrue")

    # --- Wire Logic for 1 Request ---
    builder.add_link("ZoneDemand", "out", "Demand_GT_95", "inA")
    builder.add_link("Const_95", "out", "Demand_GT_95", "inB")
    builder.add_link("Demand_GT_95", "out", "NumericSwitch_1_Req", "inSwitch")
    builder.add_link("Const_1_Req", "out", "NumericSwitch_1_Req", "inTrue")

    # --- Wire Final Prioritization ---
    builder.add_link("NumericSwitch_3_Req", "out", "Maximum", "inA")
    builder.add_link("NumericSwitch_2_Req", "out", "Maximum", "inB")
    builder.add_link("NumericSwitch_1_Req", "out", "Maximum", "inC")
    builder.add_link("Maximum", "out", "VAVCoolingRequestsTotal", "in16")


    # 5. Save the file.
    bog_filename = f"{script_filename}.bog"
    output_path = os.path.join(args.output_dir, bog_filename)
    os.makedirs(args.output_dir, exist_ok=True)
    builder.save(output_path)
    print(f"\nSuccessfully created Niagara .bog file at: {output_path}")


if __name__ == "__main__":
    main()
