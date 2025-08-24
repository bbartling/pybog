import sys
import os
import argparse

from bog_builder import BogFolderBuilder


def main():
    parser = argparse.ArgumentParser(
        description="Build a .bog file for central plant dual pump lead and lag staging logic."
    )
    parser.add_argument(
        "-o", "--output_dir", default="examples", help="Output directory."
    )
    args = parser.parse_args()

    script_filename = os.path.basename(__file__).replace(".py", "")
    # Use a descriptive name for the overall logic container
    builder = BogFolderBuilder("PumpLeadLagStaging")

    # --- Top-level Inputs ---
    # Boolean point to select lead pump: True = Pump 1 Lead, False = Pump 2 Lead
    builder.add_boolean_writable(name="LeadPump1_Select", default_value=True)
    # Pump status feedbacks (actual running state)
    builder.add_boolean_writable(name="Pump1_Status", default_value=True)
    builder.add_boolean_writable(name="Pump2_Status", default_value=True)

    # --- Top-level Outputs ---
    # Pump commands (True = ON, False = OFF)
    builder.add_boolean_writable(name="Pump1_Command")
    builder.add_boolean_writable(name="Pump2_Command")
    # Indication if the currently active lead pump has failed
    builder.add_boolean_writable(name="LeadPumpFailure")

    # --- Logic Sub-Folder ---
    builder.start_sub_folder("StagingLogic")

    # --- Constants ---
    builder.add_component(
        "kitControl:NumericConst", name="Num_0", properties={"out": 0.0}
    )
    builder.add_component(
        "kitControl:NumericConst", name="Num_1", properties={"out": 1.0}
    )

    # --- Determine if P1 is the designated lead pump (outputs b:Boolean) ---
    # An Equal block is used here to take the 'BooleanWritableExt' type from 'LeadPump1_Select'
    # and output a pure 'b:Boolean' type. This pure boolean is required for the 'inSwitch'
    # slot of 'NumericSwitch' components, preventing the previous type mismatch error.
    # The builder will automatically insert necessary conversion links for inputs to 'Equal'.
    builder.add_component("kitControl:Equal", name="P1_IsLeadBool")
    builder.add_link("LeadPump1_Select", "out", "P1_IsLeadBool", "inA")
    builder.add_link("Num_1", "out", "P1_IsLeadBool", "inB")

    # Determine if P2 is the designated lead pump (outputs b:Boolean)
    builder.add_component("kitControl:Not", name="P2_IsLeadBool")
    builder.add_link("P1_IsLeadBool", "out", "P2_IsLeadBool", "in")

    # --- Determine if pumps are 'Not Running' (outputs b:Boolean) ---
    # Converts PumpX_Status (BooleanWritableExt) to b:Boolean, then inverts it.
    builder.add_component("kitControl:Not", name="Not_P1_Status")
    builder.add_link("Pump1_Status", "out", "Not_P1_Status", "in")

    builder.add_component("kitControl:Not", name="Not_P2_Status")
    builder.add_link("Pump2_Status", "out", "Not_P2_Status", "in")

    # --- Detect Lead Pump Failure Condition for each potential lead pump ---
    # A pump is considered "failed" in its lead role if it's currently designated as lead
    # AND its physical status indicates it is not running (i.e., commanded ON but OFF).
    builder.add_component(
        "kitControl:And", name="P1_LeadFailureCondition"
    )  # Output is b:Boolean
    builder.add_link("P1_IsLeadBool", "out", "P1_LeadFailureCondition", "inA")
    builder.add_link("Not_P1_Status", "out", "P1_LeadFailureCondition", "inB")

    builder.add_component(
        "kitControl:And", name="P2_LeadFailureCondition"
    )  # Output is b:Boolean
    builder.add_link("P2_IsLeadBool", "out", "P2_LeadFailureCondition", "inA")
    builder.add_link("Not_P2_Status", "out", "P2_LeadFailureCondition", "inB")

    # --- Logic Path: Pump 1 is Designated Lead ---
    # This set of NumericSwitches determines the commands and failure status
    # IF Pump 1 is the lead pump, based on whether Pump 1 has failed.
    builder.add_numeric_switch(
        name="P1_Cmd_Path_P1Lead"
    )  # Controls P1 command if P1 is designated lead
    builder.add_link("P1_LeadFailureCondition", "out", "P1_Cmd_Path_P1Lead", "inSwitch")
    builder.add_link(
        "Num_0", "out", "P1_Cmd_Path_P1Lead", "inTrue"
    )  # P1 OFF if P1 lead and failed
    builder.add_link(
        "Num_1", "out", "P1_Cmd_Path_P1Lead", "inFalse"
    )  # P1 ON if P1 lead and OK

    builder.add_numeric_switch(
        name="P2_Cmd_Path_P1Lead"
    )  # Controls P2 command if P1 is designated lead
    builder.add_link("P1_LeadFailureCondition", "out", "P2_Cmd_Path_P1Lead", "inSwitch")
    builder.add_link(
        "Num_1", "out", "P2_Cmd_Path_P1Lead", "inTrue"
    )  # P2 ON (lag takeover) if P1 lead and failed
    builder.add_link(
        "Num_0", "out", "P2_Cmd_Path_P1Lead", "inFalse"
    )  # P2 OFF if P1 lead and OK

    builder.add_numeric_switch(
        name="LeadFail_Path_P1Lead"
    )  # Controls LeadPumpFailure if P1 is designated lead
    builder.add_link(
        "P1_LeadFailureCondition", "out", "LeadFail_Path_P1Lead", "inSwitch"
    )
    builder.add_link(
        "Num_1", "out", "LeadFail_Path_P1Lead", "inTrue"
    )  # Lead pump failed
    builder.add_link("Num_0", "out", "LeadFail_Path_P1Lead", "inFalse")  # Lead pump OK

    # --- Logic Path: Pump 2 is Designated Lead ---
    # This set of NumericSwitches determines the commands and failure status
    # IF Pump 2 is the lead pump, based on whether Pump 2 has failed.
    builder.add_numeric_switch(
        name="P1_Cmd_Path_P2Lead"
    )  # Controls P1 command if P2 is designated lead
    builder.add_link("P2_LeadFailureCondition", "out", "P1_Cmd_Path_P2Lead", "inSwitch")
    builder.add_link(
        "Num_1", "out", "P1_Cmd_Path_P2Lead", "inTrue"
    )  # P1 ON (lag takeover) if P2 lead and failed
    builder.add_link(
        "Num_0", "out", "P1_Cmd_Path_P2Lead", "inFalse"
    )  # P1 OFF if P2 lead and OK

    builder.add_numeric_switch(
        name="P2_Cmd_Path_P2Lead"
    )  # Controls P2 command if P2 is designated lead
    builder.add_link("P2_LeadFailureCondition", "out", "P2_Cmd_Path_P2Lead", "inSwitch")
    builder.add_link(
        "Num_0", "out", "P2_Cmd_Path_P2Lead", "inTrue"
    )  # P2 OFF if P2 lead and failed
    builder.add_link(
        "Num_1", "out", "P2_Cmd_Path_P2Lead", "inFalse"
    )  # P2 ON if P2 lead and OK

    builder.add_numeric_switch(
        name="LeadFail_Path_P2Lead"
    )  # Controls LeadPumpFailure if P2 is designated lead
    builder.add_link(
        "P2_LeadFailureCondition", "out", "LeadFail_Path_P2Lead", "inSwitch"
    )
    builder.add_link(
        "Num_1", "out", "LeadFail_Path_P2Lead", "inTrue"
    )  # Lead pump failed
    builder.add_link("Num_0", "out", "LeadFail_Path_P2Lead", "inFalse")  # Lead pump OK

    # --- Final Output Selection ---
    # These switches select between the "P1 Lead path" results and "P2 Lead path" results
    # based on which pump is currently designated as lead by 'P1_IsLeadBool'.
    builder.add_numeric_switch(name="Final_P1_Cmd")
    builder.add_link("P1_IsLeadBool", "out", "Final_P1_Cmd", "inSwitch")
    builder.add_link(
        "P1_Cmd_Path_P1Lead", "out", "Final_P1_Cmd", "inTrue"
    )  # Use P1 cmd from P1 lead path
    builder.add_link(
        "P1_Cmd_Path_P2Lead", "out", "Final_P1_Cmd", "inFalse"
    )  # Use P1 cmd from P2 lead path

    builder.add_numeric_switch(name="Final_P2_Cmd")
    builder.add_link("P1_IsLeadBool", "out", "Final_P2_Cmd", "inSwitch")
    builder.add_link(
        "P2_Cmd_Path_P1Lead", "out", "Final_P2_Cmd", "inTrue"
    )  # Use P2 cmd from P1 lead path
    builder.add_link(
        "P2_Cmd_Path_P2Lead", "out", "Final_P2_Cmd", "inFalse"
    )  # Use P2 cmd from P2 lead path

    builder.add_numeric_switch(name="Final_Lead_Failure")
    builder.add_link("P1_IsLeadBool", "out", "Final_Lead_Failure", "inSwitch")
    builder.add_link(
        "LeadFail_Path_P1Lead", "out", "Final_Lead_Failure", "inTrue"
    )  # Use failure status from P1 lead path
    builder.add_link(
        "LeadFail_Path_P2Lead", "out", "Final_Lead_Failure", "inFalse"
    )  # Use failure status from P2 lead path

    builder.end_sub_folder()

    # --- Link Final Numeric Outputs (0/1) to Top-Level BooleanWritable Points ---
    # The BogFolderBuilder should automatically add StatusNumericToStatusBoolean conversion links here.
    builder.add_link("Final_P1_Cmd", "out", "Pump1_Command", "in16")
    builder.add_link("Final_P2_Cmd", "out", "Pump2_Command", "in16")
    builder.add_link("Final_Lead_Failure", "out", "LeadPumpFailure", "in16")

    # --- Save the .bog file ---
    bog_filename = "pump_lead_lag.bog"
    output_path = os.path.join(args.output_dir, bog_filename)
    os.makedirs(args.output_dir, exist_ok=True)
    builder.save(output_path)
    print(
        f"\nSuccessfully created Niagara .bog file at: {os.path.abspath(output_path)}"
    )


if __name__ == "__main__":
    main()
