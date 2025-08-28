"""
hvac_g36_ahu_supply_temp_reset.py

Made and validated in field by pybog creator.

Final version was a slow build off of ping pong, linear_reset_examples,
multivibrator_link_test, rate_of_change_limiter,
 and numeric_delay_playground examples.

Duct static reset and supply air temp reset algorith very similar.

This script builds a wiresheet implementation of the ASHRAE Guideline 36
Supply Air Temperature (SAT) Trim & Respond algorithm, based on a proven
Java program object. This version is structurally identical to the robust
duct static pressure version, including startup initialization and delays.

Algorithm Overview:
-------------------
1.  **Core Engine:** A Trim & Respond (T&R) counter adjusts an internal
    variable called 'tMaxState'. This is the maximum allowed SAT at the
    lowest OAT.
    - If cooling requests are low, 'tMaxState' is trimmed UP (allowing warmer supply air).
    - If cooling requests are high, 'tMaxState' is responded DOWN (demanding colder supply air).
2.  **OAT Reset:** The final SAT setpoint is calculated using a linear reset
    (interpolation) based on the current OAT and the calculated 'tMaxState'.
3.  **State Management:** The T&R engine is only active when the fan has been
    running for a specified startup delay. When the fan is off or during the
    startup delay, 'tMaxState' is reset to its absolute maximum (SatMax).
4.  **Clamping & Delays:** All calculated values are clamped within their defined
    min/max limits, and a NumericDelay is used to smooth the minimum clamp
    value after startup, preventing erratic behavior.
"""

import sys, os, argparse
from bog_builder import BogFolderBuilder


def main():
    p = argparse.ArgumentParser(
        description="Build a G36 AHU SAT Trim & Respond .bog file."
    )
    p.add_argument("-o", "--output_dir", default="examples")
    args = p.parse_args()

    b = BogFolderBuilder("G36AhuSupTempTrimAndRespond", debug=True)

    sat_max = 70.0

    # --- Top-level I/O and Configuration ---
    b.add_boolean_writable("Fan_Status", default_value=False)
    b.add_numeric_writable("TotalRequests", default_value=0.0, precision=0)
    b.add_numeric_writable("OutsideAirTemp", default_value=72.0, precision=1)
    b.add_boolean_writable("Enabled", default_value=True)
    b.add_boolean_writable("ManualReset", default_value=False)

    # SAT Reset Configuration
    b.add_numeric_writable("SatMin", default_value=55.0, precision=1)
    b.add_numeric_writable("SatMax", default_value=sat_max, precision=1)
    b.add_numeric_writable("OatMin", default_value=60.0, precision=1)
    b.add_numeric_writable("OatMax", default_value=75.0, precision=1)

    # T&R Tuning
    b.add_numeric_writable("SPtrim", default_value=0.2, precision=2)
    b.add_numeric_writable("SPres", default_value=-0.3, precision=2)
    b.add_numeric_writable("SPResMax", default_value=-1.0, precision=2)
    b.add_numeric_writable("Ignore", default_value=2.0, precision=0)

    # Timers
    b.add_numeric_writable("UpdateMinutes", default_value=2.0)
    b.add_numeric_writable("StartupDelayMinutes", default_value=10.0)

    # Final Output
    b.add_numeric_writable("Output_SAT_Setpoint", default_value=sat_max, precision=2)

    # --- Logic Components ---
    b.start_sub_folder("Logic")
    b.add_component("kitControl:And", "EnableGate")
    b.add_component("kitControl:BooleanDelay", "StartupDelay")
    b.add_component("kitControl:And", "RunLogicEnable")
    b.add_component(
        "kitControl:NumericConst", "Const_60000", properties={"value": 60000.0}
    )
    b.add_component("kitControl:Multiply", "Delay_ms_Calc")

    # this correct some odd quark in flow programming to smooth
    # start up values after startup delay expires
    b.add_numeric_writable("MaxStepSize", default_value=0.1, precision=2)
    b.add_numeric_writable("MinClampDelayMinutes", default_value=1.0)

    # Update Timer
    b.add_component("kitControl:MultiVibrator", "UpdateTimer")
    b.add_component("kitControl:Multiply", "Update_ms_Calc")
    b.add_component("kitControl:OneShot", "UpdatePulse")
    b.add_component("kitControl:And", "PulseGate")

    # Trim vs Respond Logic
    b.add_component("kitControl:GreaterThan", "IsRespondCondition")
    b.add_component("kitControl:Subtract", "ExcessRequests")

    b.add_component("kitControl:Multiply", "ProportionalResponse")
    b.add_component(
        "kitControl:Maximum", "CappedResponse"
    )  # Use Maximum for negative response cap

    b.add_numeric_switch("AdjustmentSwitch")

    # tMaxState Counter Core
    b.add_component("kitControl:NumericLatch", "tMaxState_Latch")
    b.add_component("kitControl:Add", "New_tMaxState_Unclamped")
    b.add_component("kitControl:Minimum", "tMaxState_Clamp_Hi")
    b.add_component("kitControl:Maximum", "tMaxState_Clamp_Lo")
    b.add_numeric_switch("ResetSwitch")

    # Latch Initialization Logic (like duct static version)
    b.add_component("kitControl:OneShot", "InitializeLatchPulse")
    b.add_numeric_switch("LatchInputSwitch")

    # Dynamic Minimum Clamp Logic (like duct static version)
    b.add_numeric_switch("MinClampSwitch")

    # dont define a properties={"": 0.5} for NumericDelay just
    # wire in a numeric writeable for that as shown below
    b.add_component("kitControl:NumericDelay", "MinClampDelay")
    b.add_component("kitControl:Multiply", "MinClampDelay_ms_Calc")

    # Reset Logic
    b.add_component("kitControl:Not", "FanIsOff")
    b.add_component("kitControl:Or", "ResetTrigger")
    b.add_component("kitControl:OneShot", "ResetPulse")

    b.add_component("kitControl:Reset", "SAT_Reset_By_OAT")
    b.end_sub_folder()

    # --- Wiring ---

    # State Management
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

    # T&R Timer
    b.add_link("UpdateMinutes", "out", "Update_ms_Calc", "inA")
    b.add_link("Const_60000", "out", "Update_ms_Calc", "inB")
    b.add_link("Update_ms_Calc", "out", "UpdateTimer", "Period")
    b.add_link("UpdateTimer", "out", "UpdatePulse", "in")
    b.add_link("UpdatePulse", "out", "PulseGate", "inA")
    b.add_link("RunLogicEnable", "out", "PulseGate", "inB")

    # T&R Adjustment Calculation
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

    # tMaxState Counter and Clamping
    b.add_link("tMaxState_Latch", "out", "New_tMaxState_Unclamped", "inA")
    b.add_link("AdjustmentSwitch", "out", "New_tMaxState_Unclamped", "inB")
    b.add_link("New_tMaxState_Unclamped", "out", "tMaxState_Clamp_Hi", "inA")
    b.add_link("SatMax", "out", "tMaxState_Clamp_Hi", "inB")

    # Dynamic Minimum Clamp with Delay
    b.add_link("StartupDelay", "out", "MinClampSwitch", "inSwitch")
    b.add_link("SatMin", "out", "MinClampSwitch", "inTrue")
    b.add_link(
        "SatMax", "out", "MinClampSwitch", "inFalse"
    )  # During startup, min clamp is SatMax
    b.add_link("MinClampSwitch", "out", "MinClampDelay", "in")
    b.add_link("MinClampDelayMinutes", "out", "MinClampDelay_ms_Calc", "inA")
    b.add_link("Const_60000", "out", "MinClampDelay_ms_Calc", "inB")

    b.add_link("MaxStepSize", "out", "MinClampDelay", "maxStepSize")
    b.add_link(
        "MinClampDelay_ms_Calc",
        "out",
        "MinClampDelay",
        "updateTime",
        link_type="b:ConversionLink",
        converter_type="conv:StatusNumericToRelTime",
    )

    b.add_link("tMaxState_Clamp_Hi", "out", "tMaxState_Clamp_Lo", "inA")
    b.add_link("MinClampDelay", "out", "tMaxState_Clamp_Lo", "inB")  # Use delayed min

    # Reset Logic for tMaxState
    b.add_link("Fan_Status", "out", "FanIsOff", "in")
    b.add_link("ManualReset", "out", "ResetTrigger", "inA")
    b.add_link("FanIsOff", "out", "ResetTrigger", "inB")
    b.add_link("ResetTrigger", "out", "ResetPulse", "in")
    b.add_link("ResetPulse", "out", "ResetSwitch", "inSwitch")
    b.add_link("SatMax", "out", "ResetSwitch", "inTrue")
    b.add_link("tMaxState_Clamp_Lo", "out", "ResetSwitch", "inFalse")

    # Latching the new tMaxState value with initialization
    b.add_link("RunLogicEnable", "out", "InitializeLatchPulse", "in")
    b.add_link("InitializeLatchPulse", "out", "LatchInputSwitch", "inSwitch")
    b.add_link("SatMax", "out", "LatchInputSwitch", "inTrue")  # Initialize to SatMax
    b.add_link("ResetSwitch", "out", "LatchInputSwitch", "inFalse")
    b.add_link("LatchInputSwitch", "out", "tMaxState_Latch", "in")
    b.add_link("PulseGate", "out", "tMaxState_Latch", "clock")

    # -------- Rewritten OAT Reset wiring (Reverse-Acting) --------
    # At OatMin (low OAT) => high SAT (tMaxState_Latch)
    # At OatMax (high OAT) => low SAT (SatMin)
    b.add_link("OutsideAirTemp", "out", "SAT_Reset_By_OAT", "inA")
    b.add_link("OatMin", "out", "SAT_Reset_By_OAT", "inputLowLimit")
    b.add_link("OatMax", "out", "SAT_Reset_By_OAT", "inputHighLimit")
    b.add_link(
        "tMaxState_Latch", "out", "SAT_Reset_By_OAT", "outputLowLimit"
    )  # reverse mapping
    b.add_link(
        "SatMin", "out", "SAT_Reset_By_OAT", "outputHighLimit"
    )  # reverse mapping

    # Final Output
    b.add_link("SAT_Reset_By_OAT", "out", "Output_SAT_Setpoint", "in16")

    # --- Save File ---
    os.makedirs(args.output_dir, exist_ok=True)
    out = os.path.join(args.output_dir, "g36_supply_temp_reset_tr.bog")
    b.save(out)
    print(f"Created {out}")


if __name__ == "__main__":
    main()
