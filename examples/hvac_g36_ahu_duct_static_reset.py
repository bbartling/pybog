"""
G36-Style Trim & Respond Algorithm (Corrected)

This script builds a wiresheet implementation of a "Trim & Respond" style
algorithm, often used for duct static pressure reset as described in
ASHRAE Guideline 36. The core of the logic is a value that "pings-pongs"
or oscillates between a minimum (SPmin) and maximum (SPmax) limit.

This version has been rewritten to use a kitControl:Counter block, inspired
by the simpler ping_pong_algorithm. This approach is more direct and robust
for this type of oscillating logic. It uses a single 'Step' value for both
incrementing and decrementing. This version correctly uses the 'preset'
action to initialize the counter from SP0.
"""

import os, argparse
from bog_builder import BogFolderBuilder


def main():
    ap = argparse.ArgumentParser(description="Build a G36-style Trim & Respond .bog file.")
    ap.add_argument(
        "-o", "--output_dir", default="examples", help="Output directory for .bog"
    )
    args = ap.parse_args()

    b = BogFolderBuilder("G36_TrimAndRespond_PingPong", debug=True)

    # ---- Top-level I/O and Configuration ----
    b.add_boolean_writable("ManualReset", default_value=False)
    b.add_boolean_writable("Enabled", default_value=True)
    b.add_boolean_writable("Fan_Status", default_value=False)
    b.add_numeric_writable("SP0", default_value=1.0, precision=2)
    b.add_numeric_writable("SPmin", default_value=0.40, precision=2)
    b.add_numeric_writable("SPmax", default_value=1.25, precision=2)
    b.add_numeric_writable("Step", default_value=0.04, precision=2)
    b.add_numeric_writable("Output")
    
    UpdateMinutes_default = 0.5
    b.add_numeric_writable("UpdateMinutes", default_value=UpdateMinutes_default)
    
    StartUpDelayMinutes_default = 0.5
    b.add_numeric_writable("StartUpDelayMinutes", default_value=StartUpDelayMinutes_default)


    # ---- Logic subfolders ----
    b.start_sub_folder("StateManagement")
    # Detect rising edge of Fan_Status to start the timer
    b.add_component("kitControl:BooleanLatch", "FanOnLatch")
    b.add_component("kitControl:Not", "NotFanStatus")
    # Startup delay timer (onDelay is now wired dynamically)
    b.add_component("kitControl:BooleanDelay", "StartupDelayTimer")
    # Components to convert minutes to milliseconds for the delay
    b.add_component("kitControl:NumericConst", "Const_60000", properties={"value": 60000.0})
    b.add_component("kitControl:Multiply", "Delay_ms_Calc")
    b.add_numeric_writable("CalculatedDelay_ms")
    # The main logic is enabled only after the fan is on AND the startup delay is met
    b.add_component("kitControl:And", "RunLogicEnable")
    b.end_sub_folder()

    b.start_sub_folder("Logic")
    
    # Timer components
    b.add_component(
        "kitControl:MultiVibrator", "MultiVibrator", properties={"period": str(int(UpdateMinutes_default * 60 * 1000))}
    )
    b.add_component("kitControl:NumericConst", "Const_60000_Update", properties={"value": 60000.0})
    b.add_component("kitControl:Multiply", "Update_ms_Display")
    b.add_numeric_writable("CalculatedPeriod_ms")
    b.add_component("kitControl:OneShot", "FireOneShot")
    b.add_component("kitControl:And", "RunPermission")
    b.add_component("kitControl:And", "PulseGate")

    # Core Counter Logic
    b.add_counter("Counter") # Initial value is now handled by preset logic
    b.add_component("kitControl:GreaterThanEqual", "Hit_SPmax")
    b.add_component("kitControl:LessThanEqual", "Hit_SPmin")
    b.add_component("kitControl:Or", "Hit_Any_Limit")
    b.add_component("kitControl:BooleanLatch", "DirectionLatch")
    b.add_boolean_switch("CountUp_Switch")
    b.add_boolean_switch("CountDown_Switch")
    
    # Reset Logic
    b.add_component("kitControl:Not", "FanIsOff")
    b.add_component("kitControl:Or", "ResetTrigger")
    b.add_component("kitControl:OneShot", "ResetOneShot")
    
    # Final Output Selection
    b.add_numeric_switch("FinalOutput_Switch")

    b.end_sub_folder()

    # ---- Wiring ----
    
    # State Management Wiring
    b.add_link("Fan_Status", "out", "NotFanStatus", "in")
    b.add_link("Fan_Status", "out", "FanOnLatch", "clock")
    b.add_link("NotFanStatus", "out", "FanOnLatch", "in") 
    b.add_link("FanOnLatch", "out", "StartupDelayTimer", "in")
    
    # Dynamic Startup Delay Calculation
    b.add_link("StartUpDelayMinutes", "out", "Delay_ms_Calc", "inA")
    b.add_link("Const_60000", "out", "Delay_ms_Calc", "inB")
    b.add_link("Delay_ms_Calc", "out", "CalculatedDelay_ms", "in16")
    b.add_link(
        "CalculatedDelay_ms", "out", "StartupDelayTimer", "onDelay", 
        link_type="b:ConversionLink", converter_type="conv:StatusNumericToRelTime"
    )

    b.add_link("Fan_Status", "out", "RunLogicEnable", "inA")
    b.add_link("StartupDelayTimer", "out", "RunLogicEnable", "inB")

    # Timer Configuration and Pulse Generation
    b.add_link("UpdateMinutes", "out", "Update_ms_Display", "inA")
    b.add_link("Const_60000_Update", "out", "Update_ms_Display", "inB")
    b.add_link("Update_ms_Display", "out", "CalculatedPeriod_ms", "in16")
    b.add_link("CalculatedPeriod_ms", "out", "MultiVibrator", "Period")
    b.add_link("MultiVibrator", "out", "FireOneShot", "in")
    
    # Gate the pulse with Enabled and the main RunLogicEnable signal
    b.add_link("Enabled", "out", "RunPermission", "inA")
    b.add_link("RunLogicEnable", "out", "RunPermission", "inB")
    b.add_link("FireOneShot", "out", "PulseGate", "inA")
    b.add_link("RunPermission", "out", "PulseGate", "inB")

    # Limit Detection (driven by the Counter's output)
    b.add_link("Counter", "out", "Hit_SPmax", "inA")
    b.add_link("SPmax", "out", "Hit_SPmax", "inB")
    b.add_link("Counter", "out", "Hit_SPmin", "inA")
    b.add_link("SPmin", "out", "Hit_SPmin", "inB")

    # Direction Latching Logic
    b.add_link("Hit_SPmax", "out", "Hit_Any_Limit", "inA")
    b.add_link("Hit_SPmin", "out", "Hit_Any_Limit", "inB")
    b.add_link("Hit_Any_Limit", "out", "DirectionLatch", "clock")
    b.add_link("Hit_SPmax", "out", "DirectionLatch", "in")

    # Routing the pulse to CountUp or CountDown
    b.add_link("DirectionLatch", "out", "CountUp_Switch", "inSwitch")
    b.add_link("DirectionLatch", "out", "CountDown_Switch", "inSwitch")
    b.add_link("PulseGate", "out", "CountUp_Switch", "inFalse") # Count up when latch is false
    b.add_link("PulseGate", "out", "CountDown_Switch", "inTrue") # Count down when latch is true

    # Counter Wiring
    b.add_link("Step", "out", "Counter", "countIncrement")
    b.add_link("CountUp_Switch", "out", "Counter", "countUp")
    b.add_link("CountDown_Switch", "out", "Counter", "countDown")
    
    # Reset Logic using Preset
    b.add_link("Fan_Status", "out", "FanIsOff", "in")
    b.add_link("ManualReset", "out", "ResetTrigger", "inA")
    b.add_link("FanIsOff", "out", "ResetTrigger", "inB")
    b.add_link("ResetTrigger", "out", "ResetOneShot", "in")
    b.add_link("ResetOneShot", "out", "Counter", "presetValue") # Use preset action
    b.add_link("SP0", "out", "Counter", "presetValue") # Link SP0 to presetValue
    
    # Final Output Selection
    b.add_link("RunLogicEnable", "out", "FinalOutput_Switch", "inSwitch")
    b.add_link("Counter", "out", "FinalOutput_Switch", "inTrue") # If running, use the counter value
    b.add_link("SP0", "out", "FinalOutput_Switch", "inFalse") # If off or in delay, use SP0
    b.add_link("FinalOutput_Switch", "out", "Output", "in16")

    # ---- Save ----
    os.makedirs(args.output_dir, exist_ok=True)
    out = os.path.join(args.output_dir, "g36_trim_respond_ping_pong.bog")
    b.save(out)
    print(f"Created Niagara .bog at: {os.path.abspath(out)}")


if __name__ == "__main__":
    main()
