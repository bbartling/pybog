"""
[WARNING - INTENTIONALLY INCORRECT FILE]
This script is a deliberate example of an improperly constructed bog builder
file. It is designed to fail during execution and produce validation warnings
and errors.

The purpose of this file is to serve as a negative example for an LLM agent,
demonstrating common mistakes such as:
1.  Using incorrect component types (e.g., 'kitControl:NumericLatch' which
    may not exist or be typed correctly).
2.  Attempting to link to invalid component slots (e.g., linking a numeric
    value to the 'onDelay' property of a BooleanDelay instead of its 'in' slot).
3.  General syntax that will be caught by the bog_builder's internal
    validation and raise a ValueError.

This script should be used to test an agent's ability to recognize, parse,
and potentially learn from builder script failures. DO NOT use this script
as a template for valid logic.
"""


import sys
import os
import argparse

from bog_builder import BogFolderBuilder

def main():
    """
    This script builds the wiresheet logic for the AHU Supply Air Temperature (SAT)
    Trim & Respond program, based on the provided Java example.
    """
    parser = argparse.ArgumentParser(
        description="Build a .bog file for the SAT Trim and Respond logic."
    )
    parser.add_argument(
        "-o", "--output_dir", default="examples", help="Output directory for the .bog file."
    )
    args = parser.parse_args()

    script_filename = os.path.basename(__file__).replace(".py", "")
    builder = BogFolderBuilder("SatTrimAndRespond")

    # --- Inputs ---
    print("Creating top-level inputs...")
    builder.add_numeric_writable("TotalRequests", default_value=0.0)
    builder.add_boolean_writable("FanRunCmd", default_value=False)
    builder.add_numeric_writable("OutsideAirTemp", default_value=65.0)
    builder.add_numeric_writable("SatMin", default_value=55.0)
    builder.add_numeric_writable("SatMax", default_value=70.0)
    builder.add_numeric_writable("OatMin", default_value=60.0)
    builder.add_numeric_writable("OatMax", default_value=70.0)
    builder.add_numeric_writable("StartUpDelayMinutes", default_value=10.0)
    builder.add_numeric_writable("UpdateMinutes", default_value=2.0)
    builder.add_numeric_writable("Ignore", default_value=2.0)
    builder.add_numeric_writable("SPtrim", default_value=0.2)
    builder.add_numeric_writable("SPres", default_value=-0.3)
    builder.add_numeric_writable("SPResMax", default_value=-1.0)

    # --- Outputs ---
    print("Creating top-level outputs...")
    builder.add_numeric_writable("DischargeAirTempSp")

    # --- Logic Sub-Folders ---
    print("Creating logic components in sub-folders...")

    # --- State and Timing Logic ---
    builder.start_sub_folder("StateLogic")
    builder.add_component("kitControl:BooleanDelay", "StartupDelay")
    builder.add_component("kitControl:MultiVibrator", "UpdateTimer")
    builder.add_component("kitControl:OneShot", "UpdatePulse")
    builder.add_component("kitControl:And", "MainLogicEnable")
    builder.add_component("kitControl:Or", "ResetTmaxCondition")
    builder.add_component("kitControl:Not", "FanNotRunning")
    builder.end_sub_folder()

    # --- Trim & Respond Core Logic ---
    builder.start_sub_folder("TrimRespondLogic")
    builder.add_component("kitControl:GreaterThan", "RequestsExceedIgnore")
    builder.add_numeric_switch("TrimOrRespondSwitch")
    builder.add_component("kitControl:Subtract", "RespondCalc1")
    builder.add_component("kitControl:Multiply", "RespondCalc2")
    builder.add_component("kitControl:Maximum", "RespondAmount")
    builder.add_component("kitControl:Add", "TrimTmax")
    builder.add_component("kitControl:Add", "RespondTmax")
    builder.add_numeric_switch("TmaxMux")
    builder.add_component("kitControl:NumericLatch", "TmaxState")
    builder.end_sub_folder()

    # --- Interpolation Logic ---
    builder.start_sub_folder("InterpolationLogic")
    builder.add_component("kitControl:Reset", "SatSetpointInterpolator")
    builder.end_sub_folder()

    # --- Wiring ---
    print("Wiring components...")

    # --- StateLogic Wiring ---
    builder.add_link("FanRunCmd", "out", "StartupDelay", "in")
    builder.add_link("StartUpDelayMinutes", "out", "StartupDelay", "onDelay",
                     link_type="b:ConversionLink", converter_type="conv:StatusNumericToNumber")

    builder.add_link("UpdateMinutes", "out", "UpdateTimer", "period",
                     link_type="b:ConversionLink", converter_type="conv:StatusNumericToNumber")
    builder.add_link("UpdateTimer", "out", "UpdatePulse", "in")

    builder.add_link("StartupDelay", "out", "MainLogicEnable", "inA")
    builder.add_link("UpdatePulse", "out", "MainLogicEnable", "inB")

    builder.add_link("FanRunCmd", "out", "FanNotRunning", "in")
    builder.add_link("FanNotRunning", "out", "ResetTmaxCondition", "inA")
    # This is a simplification: we reset tMax when the fan is off OR on the first pulse
    builder.add_link("UpdatePulse", "out", "ResetTmaxCondition", "inB")


    # --- TrimRespondLogic Wiring ---
    builder.add_link("TotalRequests", "out", "RequestsExceedIgnore", "inA")
    builder.add_link("Ignore", "out", "RequestsExceedIgnore", "inB")

    builder.add_link("RequestsExceedIgnore", "out", "TrimOrRespondSwitch", "inSwitch")
    builder.add_link("TrimTmax", "out", "TrimOrRespondSwitch", "inFalse")
    builder.add_link("RespondTmax", "out", "TrimOrRespondSwitch", "inTrue")

    builder.add_link("TotalRequests", "out", "RespondCalc1", "inA")
    builder.add_link("Ignore", "out", "RespondCalc1", "inB")
    builder.add_link("RespondCalc1", "out", "RespondCalc2", "inA")
    builder.add_link("SPres", "out", "RespondCalc2", "inB")
    builder.add_link("RespondCalc2", "out", "RespondAmount", "inA")
    builder.add_link("SPResMax", "out", "RespondAmount", "inB")

    builder.add_link("DischargeAirTempSp", "out", "TrimTmax", "inA")
    builder.add_link("SPtrim", "out", "TrimTmax", "inB")

    builder.add_link("DischargeAirTempSp", "out", "RespondTmax", "inA")
    builder.add_link("RespondAmount", "out", "RespondTmax", "inB")

    builder.add_link("ResetTmaxCondition", "out", "TmaxMux", "inSwitch")
    builder.add_link("SatMax", "out", "TmaxMux", "inTrue")
    builder.add_link("TrimOrRespondSwitch", "out", "TmaxMux", "inFalse")

    builder.add_link("TmaxMux", "out", "TmaxState", "in")
    builder.add_link("MainLogicEnable", "out", "TmaxState", "clock")


    # --- InterpolationLogic Wiring ---
    builder.add_link("OutsideAirTemp", "out", "SatSetpointInterpolator", "inA")
    builder.add_link("OatMin", "out", "SatSetpointInterpolator", "inputLowLimit")
    builder.add_link("OatMax", "out", "SatSetpointInterpolator", "inputHighLimit")
    builder.add_link("TmaxState", "out", "SatSetpointInterpolator", "outputHighLimit")
    builder.add_link("SatMin", "out", "SatSetpointInterpolator", "outputLowLimit")

    builder.add_link("SatSetpointInterpolator", "out", "DischargeAirTempSp", "in16")


    # --- Save the File ---
    bog_filename = f"{script_filename}.bog"
    output_path = os.path.join(args.output_dir, bog_filename)
    os.makedirs(args.output_dir, exist_ok=True)
    builder.save(output_path)
    print(f"\nSuccessfully created Niagara .bog file at: {output_path}")

if __name__ == "__main__":
    main()
