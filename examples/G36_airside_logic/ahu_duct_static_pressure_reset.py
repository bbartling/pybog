import sys
import os
import argparse

# Add the 'src' directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.bog_builder_new import BogFolderBuilder


def main():
    parser = argparse.ArgumentParser(description="Build a .bog file for AHU duct static Trim & Respond with PeriodicTrigger")
    parser.add_argument("-o", "--output_dir", default="examples", help="Output directory for the .bog file.")
    args = parser.parse_args()

    script_filename = os.path.basename(__file__).replace(".py", "")
    builder = BogFolderBuilder("G36_AHU_DuctStatic_TnR")

    # -------------------------------
    # Inputs
    # -------------------------------
    builder.add_numeric_writable("Requests", 0.0)
    builder.add_numeric_writable("I", 6.0)
    builder.add_numeric_writable("Current_SP", 1.0)
    builder.add_numeric_writable("SP0", 1.25)
    builder.add_numeric_writable("SPmin", 0.6)
    builder.add_numeric_writable("SPmax", 1.75)
    builder.add_numeric_writable("SPtrim", -0.02)
    builder.add_numeric_writable("SPres", 0.04)
    builder.add_numeric_writable("SPResMax", 0.08)

    builder.add_boolean_writable("Enable_Logic", True)
    builder.add_boolean_writable("Fan_Run_Cmd", False)

    builder.add_numeric_writable("DuctStaticSP_Command")

    # -------------------------------
    # Run Condition (Td delay)
    # -------------------------------
    builder.start_sub_folder("RunCondition")
    builder.add_component("kitControl:And", "Enable_AND_Fan")
    builder.add_component("kitControl:BooleanDelay", "Fan_TrueFor_Td", properties={"onDelay": "600000"})  # 10m
    builder.end_sub_folder()

    # -------------------------------
    # Compare R vs I
    # -------------------------------
    builder.start_sub_folder("Compare_R_I")
    builder.add_component("kitControl:LessThanEqual", "R_LE_I")
    builder.end_sub_folder()

    # -------------------------------
    # Trim Path
    # -------------------------------
    builder.start_sub_folder("TrimPath")
    builder.add_component("kitControl:Add", "SP_Plus_Trim")
    builder.add_component("kitControl:Maximum", "Clamp_Min")
    builder.add_component("kitControl:Minimum", "Clamp_Max")
    builder.end_sub_folder()

    # -------------------------------
    # Respond Path
    # -------------------------------
    builder.start_sub_folder("RespondPath")
    builder.add_component("kitControl:Subtract", "R_minus_I")
    builder.add_component("kitControl:Multiply", "SPres_times_RminusI")
    builder.add_component("kitControl:Minimum", "RespondAmount_Capped")
    builder.add_component("kitControl:Add", "SP_Plus_Respond")
    builder.add_component("kitControl:Maximum", "Clamp_Min_Resp")
    builder.add_component("kitControl:Minimum", "Clamp_Max_Resp")
    builder.end_sub_folder()

    # -------------------------------
    # Select Trim or Respond
    # -------------------------------
    builder.start_sub_folder("SelectTrimOrRespond")
    builder.add_numeric_switch("TrimOrRespond_Switch")
    builder.end_sub_folder()

    # -------------------------------
    # Gate by RunCondition
    # -------------------------------
    builder.start_sub_folder("RunGate")
    builder.add_numeric_switch("RunEnabled_Switch")
    builder.end_sub_folder()

    # -------------------------------
    # Periodic Trigger (T delay between adjustments)
    # -------------------------------
    builder.start_sub_folder("AdjustRateLimit")
    builder.add_component("kitControl:PeriodicTrigger", "Adjust_Trigger", properties={"period": "120000"})  # 2m
    builder.add_numeric_switch("RateLimited_Switch")
    builder.end_sub_folder()

    # -------------------------------
    # Reset-to-initial on fan start
    # -------------------------------
    builder.start_sub_folder("InitReset")
    builder.add_component("kitControl:OneShot", "FanStart_OneShot")
    builder.add_numeric_switch("InitReset_Switch")
    builder.end_sub_folder()

    # -------------------------------
    # Wiring
    # -------------------------------
    # RunCondition
    builder.add_link("Enable_Logic", "out", "Enable_AND_Fan", "inA")
    builder.add_link("Fan_Run_Cmd", "out", "Fan_TrueFor_Td", "in")
    builder.add_link("Fan_TrueFor_Td", "out", "Enable_AND_Fan", "inB")

    # Compare R vs I
    builder.add_link("Requests", "out", "R_LE_I", "inA")
    builder.add_link("I", "out", "R_LE_I", "inB")

    # Trim
    builder.add_link("Current_SP", "out", "SP_Plus_Trim", "inA")
    builder.add_link("SPtrim", "out", "SP_Plus_Trim", "inB")
    builder.add_link("SP_Plus_Trim", "out", "Clamp_Min", "inA")
    builder.add_link("SPmin", "out", "Clamp_Min", "inB")
    builder.add_link("Clamp_Min", "out", "Clamp_Max", "inA")
    builder.add_link("SPmax", "out", "Clamp_Max", "inB")

    # Respond
    builder.add_link("Requests", "out", "R_minus_I", "inA")
    builder.add_link("I", "out", "R_minus_I", "inB")
    builder.add_link("R_minus_I", "out", "SPres_times_RminusI", "inA")
    builder.add_link("SPres", "out", "SPres_times_RminusI", "inB")
    builder.add_link("SPres_times_RminusI", "out", "RespondAmount_Capped", "inA")
    builder.add_link("SPResMax", "out", "RespondAmount_Capped", "inB")
    builder.add_link("Current_SP", "out", "SP_Plus_Respond", "inA")
    builder.add_link("RespondAmount_Capped", "out", "SP_Plus_Respond", "inB")
    builder.add_link("SP_Plus_Respond", "out", "Clamp_Min_Resp", "inA")
    builder.add_link("SPmin", "out", "Clamp_Min_Resp", "inB")
    builder.add_link("Clamp_Min_Resp", "out", "Clamp_Max_Resp", "inA")
    builder.add_link("SPmax", "out", "Clamp_Max_Resp", "inB")

    # Trim/Respond select
    builder.add_link("R_LE_I", "out", "TrimOrRespond_Switch", "inSwitch")
    builder.add_link("Clamp_Max", "out", "TrimOrRespond_Switch", "inTrue")
    builder.add_link("Clamp_Max_Resp", "out", "TrimOrRespond_Switch", "inFalse")

    # RunCondition gate
    builder.add_link("Enable_AND_Fan", "out", "RunEnabled_Switch", "inSwitch")
    builder.add_link("TrimOrRespond_Switch", "out", "RunEnabled_Switch", "inTrue")
    builder.add_link("Current_SP", "out", "RunEnabled_Switch", "inFalse")

    # Periodic trigger gate
    builder.add_link("RunEnabled_Switch", "out", "RateLimited_Switch", "inTrue")
    builder.add_link("Current_SP", "out", "RateLimited_Switch", "inFalse")
    builder.add_link("Adjust_Trigger", "out", "RateLimited_Switch", "inSwitch")

    # Reset-to-initial
    builder.add_link("Fan_Run_Cmd", "out", "FanStart_OneShot", "in")
    builder.add_link("FanStart_OneShot", "out", "InitReset_Switch", "inSwitch")
    builder.add_link("SP0", "out", "InitReset_Switch", "inTrue")
    builder.add_link("RateLimited_Switch", "out", "InitReset_Switch", "inFalse")

    # Final output
    builder.add_link("InitReset_Switch", "out", "DuctStaticSP_Command", "in16")

    # Save
    bog_filename = f"{script_filename}.bog"
    os.makedirs(args.output_dir, exist_ok=True)
    builder.save(os.path.join(args.output_dir, bog_filename))
    print(f"Created: {os.path.join(args.output_dir, bog_filename)}")


if __name__ == "__main__":
    main()
