"""
G36 Duct Static Pressure Trim & Respond Algorithm (with SPResMax)

This script builds a robust wiresheet implementation of the ASHRAE G36
Trim & Respond algorithm, now including the SPResMax cap. This version
uses a custom counter built from fundamental logic blocks for explicit control.

Algorithm Overview (matching the Java logic):
1.  When Fan_Status is false, the output is driven to SP0.
2.  When Fan_Status becomes true, a StartupDelay holds the output at SP0.
3.  After the delay, the main logic runs on a periodic timer.
4.  On each timer pulse, the logic checks TotalRequests:
    - If <= Ignore, trim down by SPtrim.
    - If > Ignore, respond up by SPres * (Requests - Ignore), but
      the response amount is capped at a maximum of SPResMax.
5.  The final setpoint is clamped between SPmin and SPmax. During the
    startup delay, the effective minimum is held at SP0.
6.  A ManualReset or loss of Fan_Status resets the output to SP0.
"""

import sys, os, argparse
from bog_builder import BogFolderBuilder


def main():
    p = argparse.ArgumentParser(
        description="Build a G36 Trim & Respond .bog file with SPResMax."
    )
    p.add_argument("-o", "--output_dir", default="examples")
    args = p.parse_args()

    b = BogFolderBuilder("G36_TrimAndRespond_SPResMax", debug=True)

    # --- Top-level I/O and Configuration ---
    b.add_boolean_writable("Fan_Status", default_value=False)
    b.add_numeric_writable("TotalRequests", default_value=0.0, precision=0)
    b.add_boolean_writable("Enabled", default_value=True)
    b.add_boolean_writable("ManualReset", default_value=False)

    b.add_numeric_writable("SP0", default_value=1.0, precision=2)
    b.add_numeric_writable("SPmin", default_value=0.40, precision=2)
    b.add_numeric_writable("SPmax", default_value=1.25, precision=2)
    b.add_numeric_writable("SPtrim", default_value=-0.02, precision=2)
    b.add_numeric_writable("SPres", default_value=0.04, precision=2)
    b.add_numeric_writable(
        "SPResMax", default_value=0.08, precision=2
    )  # Added SPResMax
    b.add_numeric_writable("Ignore", default_value=1.0, precision=0)

    b.add_numeric_writable("UpdateMinutes", default_value=0.5)
    b.add_numeric_writable("StartupDelayMinutes", default_value=0.5)

    b.add_numeric_writable("Output", 0.0, precision=2)

    # --- Logic Components ---
    b.start_sub_folder("StateManagement")
    b.add_component("kitControl:BooleanDelay", "StartupDelay")
    b.add_component("kitControl:And", "RunLogicEnable")
    b.add_component(
        "kitControl:NumericConst", "Const_60000", properties={"value": 60000.0}
    )
    b.add_component("kitControl:Multiply", "Delay_ms_Calc")
    b.end_sub_folder()

    b.start_sub_folder("Logic")
    # Update Timer
    b.add_component("kitControl:MultiVibrator", "UpdateTimer")
    b.add_component("kitControl:Multiply", "Update_ms_Calc")
    b.add_component("kitControl:OneShot", "UpdatePulse")
    b.add_component("kitControl:And", "PulseGate")

    # Trim vs Respond Logic
    b.add_component("kitControl:GreaterThan", "IsRespondCondition")
    b.add_component("kitControl:Subtract", "ExcessRequests")

    # --- NEW: Sub-folder for SPResMax Capping Logic ---
    b.start_sub_folder("RespondCappingLogic")
    b.add_component("kitControl:Multiply", "ProportionalResponse")
    b.add_component("kitControl:Minimum", "CappedResponse")
    b.end_sub_folder()  # End RespondCappingLogic

    b.add_numeric_switch("AdjustmentSwitch")

    # Custom Counter Core
    b.add_component("kitControl:NumericLatch", "ValueLatch")
    b.add_component("kitControl:Add", "NewSetpoint_Unclamped")
    b.add_component("kitControl:Minimum", "Clamp_Hi")
    b.add_component("kitControl:Maximum", "Clamp_Lo")
    b.add_numeric_switch("ResetSwitch")
    b.add_numeric_switch("FinalOutputSwitch")

    # Latch Initialization Logic
    b.add_component("kitControl:OneShot", "InitializeLatchPulse")
    b.add_numeric_switch("LatchInputSwitch")

    # Dynamic Minimum Clamp Logic
    b.add_numeric_switch("MinClampSwitch")

    # Reset Logic
    b.add_component("kitControl:Not", "FanIsOff")
    b.add_component("kitControl:Or", "ResetTrigger")
    b.add_component("kitControl:OneShot", "ResetPulse")
    b.end_sub_folder()

    # --- Wiring ---

    # State Management & Startup Delay
    b.add_link("Fan_Status", "out", "StartupDelay", "in")
    b.add_link("StartupDelayMinutes", "out", "Delay_ms_Calc", "inA")
    b.add_link("Const_60000", "out", "Delay_ms_Calc", "inB")
    b.add_link(
        "Delay_ms_Calc",
        "out",
        "StartupDelay",
        "onDelay",
        link_type="b:ConversionLink",
        converter_type="conv:StatusNumericToRelTime",
    )
    b.add_link("Fan_Status", "out", "RunLogicEnable", "inA")
    b.add_link("StartupDelay", "out", "RunLogicEnable", "inB")

    # Timer
    b.add_link("UpdateMinutes", "out", "Update_ms_Calc", "inA")
    b.add_link("Const_60000", "out", "Update_ms_Calc", "inB")
    b.add_link(
        "Update_ms_Calc", "out", "UpdateTimer", "Period"
    )  # Uses special dual-link logic
    b.add_link("UpdateTimer", "out", "UpdatePulse", "in")
    b.add_link("UpdatePulse", "out", "PulseGate", "inA")
    b.add_link("RunLogicEnable", "out", "PulseGate", "inB")

    # Determine Adjustment Value (Trim or Respond)
    b.add_link("TotalRequests", "out", "IsRespondCondition", "inA")
    b.add_link("Ignore", "out", "IsRespondCondition", "inB")
    b.add_link("TotalRequests", "out", "ExcessRequests", "inA")
    b.add_link("Ignore", "out", "ExcessRequests", "inB")

    # Wiring for the RespondCappingLogic sub-folder
    b.add_link("ExcessRequests", "out", "ProportionalResponse", "inA")
    b.add_link("SPres", "out", "ProportionalResponse", "inB")
    b.add_link("ProportionalResponse", "out", "CappedResponse", "inA")
    b.add_link("SPResMax", "out", "CappedResponse", "inB")

    b.add_link("IsRespondCondition", "out", "AdjustmentSwitch", "inSwitch")
    b.add_link(
        "CappedResponse", "out", "AdjustmentSwitch", "inTrue"
    )  # Use the capped value
    b.add_link("SPtrim", "out", "AdjustmentSwitch", "inFalse")

    # Calculate New Setpoint (with feedback from final output)
    b.add_link("FinalOutputSwitch", "out", "NewSetpoint_Unclamped", "inA")
    b.add_link("AdjustmentSwitch", "out", "NewSetpoint_Unclamped", "inB")

    # Wire the Dynamic Minimum Clamp
    b.add_link("StartupDelay", "out", "MinClampSwitch", "inSwitch")
    b.add_link(
        "SPmin", "out", "MinClampSwitch", "inTrue"
    )  # After delay, use normal SPmin
    b.add_link(
        "SP0", "out", "MinClampSwitch", "inFalse"
    )  # During delay, use SP0 as min

    # Clamp the new setpoint
    b.add_link("NewSetpoint_Unclamped", "out", "Clamp_Hi", "inA")
    b.add_link("SPmax", "out", "Clamp_Hi", "inB")
    b.add_link("Clamp_Hi", "out", "Clamp_Lo", "inA")
    b.add_link(
        "MinClampSwitch", "out", "Clamp_Lo", "inB"
    )  # Use the output of our new switch

    # Reset Logic
    b.add_link("Fan_Status", "out", "FanIsOff", "in")
    b.add_link("ManualReset", "out", "ResetTrigger", "inA")
    b.add_link("FanIsOff", "out", "ResetTrigger", "inB")
    b.add_link("ResetTrigger", "out", "ResetPulse", "in")
    b.add_link("ResetPulse", "out", "ResetSwitch", "inSwitch")
    b.add_link("SP0", "out", "ResetSwitch", "inTrue")
    b.add_link("Clamp_Lo", "out", "ResetSwitch", "inFalse")

    # Latching the new value with initialization
    b.add_link("RunLogicEnable", "out", "InitializeLatchPulse", "in")
    b.add_link("InitializeLatchPulse", "out", "LatchInputSwitch", "inSwitch")
    b.add_link("SP0", "out", "LatchInputSwitch", "inTrue")
    b.add_link("ResetSwitch", "out", "LatchInputSwitch", "inFalse")
    b.add_link("LatchInputSwitch", "out", "ValueLatch", "in")
    b.add_link("PulseGate", "out", "ValueLatch", "clock")

    # Final Output Selection
    b.add_link("RunLogicEnable", "out", "FinalOutputSwitch", "inSwitch")
    b.add_link("ValueLatch", "out", "FinalOutputSwitch", "inTrue")
    b.add_link("SP0", "out", "FinalOutputSwitch", "inFalse")

    # Wire to Viewer
    b.add_link("FinalOutputSwitch", "out", "Output", "in16")

    os.makedirs(args.output_dir, exist_ok=True)
    out = os.path.join(args.output_dir, "g36_trim_and_respond_with_spresmax.bog")
    b.save(out)
    print(f"Created {out}")


if __name__ == "__main__":
    main()
