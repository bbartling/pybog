"""

hvac_g36_ahu_duct_static_reset.py

Made and validated in field by pybog creator.

Final version was a slow build off of ping pong, linear_reset_examples,
multivibrator_link_test, rate_of_change_limiter,
 and numeric_delay_playground examples.

Duct static reset and supply air temp reset algorith very similar.

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
    startup delay, the effective minimum is held at SP0 and is delayed
    to prevent rapid changes.
6.  A ManualReset or loss of Fan_Status resets the output to SP0.
"""

import sys, os, argparse
from bog_builder import BogFolderBuilder


def main():
    p = argparse.ArgumentParser(
        description="Build a G36 Trim & Respond for duct pressure"
    )
    p.add_argument("-o", "--output_dir", default="examples")
    args = p.parse_args()

    b = BogFolderBuilder("G36AhuDuctPressTrimAndRespond", debug=True)

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
    b.add_numeric_writable("SPResMax", default_value=0.08, precision=2)
    b.add_numeric_writable("Ignore", default_value=1.0, precision=0)

    b.add_numeric_writable("UpdateMinutes", default_value=2.0)
    b.add_numeric_writable("StartupDelayMinutes", default_value=10.0)

    b.add_numeric_writable("Output", 0.0, precision=2)

    # --- Logic Components ---
    b.start_sub_folder("Logic")
    b.add_and("EnableGate")  # NEW
    b.add_boolean_delay("StartupDelay")
    b.add_and("RunLogicEnable")
    b.add_numeric_const("Const_60000", properties={"value": 60000.0})
    b.add_multiply("Delay_ms_Calc")

    # Update Timer
    b.add_multi_vibrator("UpdateTimer")
    b.add_multiply("Update_ms_Calc")
    b.add_one_shot("UpdatePulse")
    b.add_and("PulseGate")

    # Trim vs Respond Logic
    b.add_greater_than("IsRespondCondition")
    b.add_subtract("ExcessRequests")

    b.start_sub_folder("RespondCappingLogic")
    b.add_multiply("ProportionalResponse")
    b.add_minimum("CappedResponse")
    b.end_sub_folder()

    b.add_numeric_switch("AdjustmentSwitch")

    # Custom Counter Core
    b.add_numeric_latch("ValueLatch")
    b.add_add("NewSetpoint_Unclamped")
    b.add_minimum("Clamp_Hi")
    b.add_maximum("Clamp_Lo")
    b.add_numeric_switch("ResetSwitch")
    b.add_numeric_switch("FinalOutputSwitch")

    # Latch Initialization Logic
    b.add_one_shot("InitializeLatchPulse")
    b.add_numeric_switch("LatchInputSwitch")

    # Dynamic Minimum Clamp Logic
    b.add_numeric_switch("MinClampSwitch")

    # this correct some odd quark in flow programming to smooth
    # start up values after startup delay expires
    b.add_numeric_writable("MinClampDelayMinutes", default_value=1.0)
    b.add_numeric_writable("MaxStepSize", default_value=0.1, precision=2)

    # dont define a properties={"": 0.5} for NumericDelay just
    # wire in a numeric writeable for that as shown below
    b.add_numeric_delay("MinClampDelay")
    b.add_multiply("MinClampDelay_ms_Calc")

    # Reset Logic
    b.add_not("FanIsOff")
    b.add_or("ResetTrigger")
    b.add_one_shot("ResetPulse")

    # --- Wiring ---

    # State Management & Startup Delay
    b.add_link("Fan_Status", "out", "EnableGate", "inA")
    b.add_link("Enabled", "out", "EnableGate", "inB")
    b.add_link("EnableGate", "out", "StartupDelay", "in")
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
    b.add_link("Update_ms_Calc", "out", "UpdateTimer", "Period")
    b.add_link("UpdateTimer", "out", "UpdatePulse", "in")
    b.add_link("UpdatePulse", "out", "PulseGate", "inA")
    b.add_link("RunLogicEnable", "out", "PulseGate", "inB")

    # Determine Adjustment Value (Trim or Respond)
    b.add_link("TotalRequests", "out", "IsRespondCondition", "inA")
    b.add_link("Ignore", "out", "IsRespondCondition", "inB")
    b.add_link("TotalRequests", "out", "ExcessRequests", "inA")
    b.add_link("Ignore", "out", "ExcessRequests", "inB")

    b.add_link("ExcessRequests", "out", "ProportionalResponse", "inA")
    b.add_link("SPres", "out", "ProportionalResponse", "inB")
    b.add_link("ProportionalResponse", "out", "CappedResponse", "inA")
    b.add_link("SPResMax", "out", "CappedResponse", "inB")

    b.add_link("IsRespondCondition", "out", "AdjustmentSwitch", "inSwitch")
    b.add_link("CappedResponse", "out", "AdjustmentSwitch", "inTrue")
    b.add_link("SPtrim", "out", "AdjustmentSwitch", "inFalse")

    # Calculate New Setpoint
    b.add_link("FinalOutputSwitch", "out", "NewSetpoint_Unclamped", "inA")
    b.add_link("AdjustmentSwitch", "out", "NewSetpoint_Unclamped", "inB")

    # Wire the Dynamic Minimum Clamp Switch
    b.add_link("StartupDelay", "out", "MinClampSwitch", "inSwitch")
    b.add_link("SPmin", "out", "MinClampSwitch", "inTrue")
    b.add_link("SP0", "out", "MinClampSwitch", "inFalse")

    # --- NEW: Wire the Numeric Delay for the clamp value ---
    b.add_link("MinClampSwitch", "out", "MinClampDelay", "in")
    b.add_link("MinClampDelayMinutes", "out", "MinClampDelay_ms_Calc", "inA")
    b.add_link("Const_60000", "out", "MinClampDelay_ms_Calc", "inB")

    # this correct some odd quark in flow programming to smooth
    # start up values after startup delay expires
    b.add_link("MaxStepSize", "out", "MinClampDelay", "maxStepSize")
    b.add_link(
        "MinClampDelay_ms_Calc",
        "out",
        "MinClampDelay",
        "updateTime",
        link_type="b:ConversionLink",
        converter_type="conv:StatusNumericToRelTime",
    )

    # Clamp the new setpoint using the delayed minimum
    b.add_link("NewSetpoint_Unclamped", "out", "Clamp_Hi", "inA")
    b.add_link("SPmax", "out", "Clamp_Hi", "inB")
    b.add_link("Clamp_Hi", "out", "Clamp_Lo", "inA")
    b.add_link(
        "MinClampDelay", "out", "Clamp_Lo", "inB"
    )  # Use the output of the new delay

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
    out = os.path.join(args.output_dir, "g36_duct_static_reset_tr.bog")
    b.save(out)
    print(f"Created {out}")


if __name__ == "__main__":
    main()
