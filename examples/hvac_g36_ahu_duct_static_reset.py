"""
hvac_g36_ahu_duct_static_reset.py

This script builds a wiresheet implementation of the ASHRAE Guideline 36
Duct Static Pressure Trim & Respond algorithm, based on the provided Java
program object.

Algorithm Overview:
-------------------
1.  **Fan Off State:** When the fan is off, the Duct Static Pressure Setpoint
    (DAP-SP) is driven to a defined initial value (SP0).
2.  **Startup State:** When the fan turns on, the DAP-SP is held at SP0 for a
    configurable startup delay (StartUpDelayMinutes).
3.  **Run State (Trim & Respond):** After the startup delay, the core logic runs
    on a periodic timer (UpdateMinutes).
    - If the number of VAV damper requests (TotalRequests) is below a threshold
      (Ignore), the DAP-SP is trimmed down by a small amount (SPtrim).
    - If the number of requests is above the threshold, the DAP-SP is responded
      up by an amount proportional to the number of excess requests (SPres),
      capped at a maximum response (SPResMax).
4.  **Clamping:** The final DAP-SP is always clamped between a minimum (SPmin)
    and maximum (SPmax) value.
"""

from __future__ import annotations
import argparse
import os
import sys

# Append project src directory to path for bog_builder import
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))
from bog_builder import BogFolderBuilder


def build_graph(b: BogFolderBuilder) -> None:
    """Builds the G36 Trim & Respond logic graph."""

    # ==========================================================================
    # 1. TOP-LEVEL I/O AND CONFIGURATION SETPOINTS
    # These are the primary inputs, outputs, and configuration knobs for the algorithm.
    # ==========================================================================
    b.add_boolean_writable("FanRunCmd", default_value=False)
    b.add_numeric_writable("TotalRequests", default_value=0.0, precision=0)
    b.add_numeric_writable("DischargeAirPressureSp_Out", default_value=1.25)

    # Configuration Setpoints (now at the top level for easier access)
    b.add_numeric_writable("SP0", default_value=1.25, units="u:inchesOfWater")
    b.add_numeric_writable("SPmin", default_value=0.40, units="u:inchesOfWater")
    b.add_numeric_writable("SPmax", default_value=1.75, units="u:inchesOfWater")
    b.add_numeric_writable("StartUpDelayMinutes", default_value=10.0)
    b.add_numeric_writable("UpdateMinutes", default_value=2.0)
    b.add_numeric_writable("Ignore", default_value=6.0, precision=0)
    b.add_numeric_writable("SPtrim", default_value=-0.02, units="u:inchesOfWater")
    b.add_numeric_writable("SPres", default_value=0.04, units="u:inchesOfWater")
    b.add_numeric_writable("SPResMax", default_value=0.08, units="u:inchesOfWater")

    # ==========================================================================
    # 2. STATE MANAGEMENT LOGIC
    # Determines the current operating state. The output 'RunLogicEnable' is
    # true only when the fan is on and the startup delay is met.
    # ==========================================================================
    b.start_sub_folder("StateManagement")

    # Detect the rising edge of the FanRunCmd to trigger the startup timer
    b.add_component("kitControl:BooleanLatch", "FanRunLatch")
    b.add_component("kitControl:Not", "Not_FanRun")
    b.add_link("FanRunCmd", "out", "FanRunLatch", "clock")
    b.add_link("FanRunCmd", "out", "Not_FanRun", "in")
    b.add_link("Not_FanRun", "out", "FanRunLatch", "in")

    # Startup delay timer. The onDelay is now set directly from the default value.
    b.add_component(
        "kitControl:BooleanDelay",
        "StartupDelayTimer",
        properties={"onDelay": str(int(10.0 * 60000))},  # Default 10 min
    )
    b.add_link("FanRunLatch", "out", "StartupDelayTimer", "in")

    # The core logic is enabled only when the fan is running AND the startup delay is met.
    b.add_component("kitControl:And", "RunLogicEnable")
    b.add_link("FanRunCmd", "out", "RunLogicEnable", "inA")
    b.add_link("StartupDelayTimer", "out", "RunLogicEnable", "inB")
    b.end_sub_folder()

    # ==========================================================================
    # 3. UPDATE CADENCE TIMER
    # A MultiVibrator creates the periodic pulse that triggers the T&R calculation.
    # ==========================================================================
    b.start_sub_folder("UpdateTimer")
    # The period is now set directly from the default value.
    b.add_multi_vibrator("UpdatePulse", period_ms=str(int(2.0 * 60000))) # Default 2 min
    b.add_component("kitControl:OneShot", "UpdateTrigger")
    b.add_link("UpdatePulse", "out", "UpdateTrigger", "in")
    b.end_sub_folder()

    # ==========================================================================
    # 4. CORE TRIM AND RESPOND LOGIC
    # This is where the setpoint adjustment is calculated.
    # ==========================================================================
    b.start_sub_folder("TrimRespondLogic")

    # Internal memory for the current setpoint, using a NumericLatch
    b.add_component("kitControl:NumericLatch", "CurrentSp_Latch")

    # Determine if we are in a "Trim" or "Respond" condition
    b.add_component("kitControl:GreaterThan", "IsRespondCondition")
    b.add_link("TotalRequests", "out", "IsRespondCondition", "inA")
    b.add_link("Ignore", "out", "IsRespondCondition", "inB")

    # --- Calculate the Respond amount ---
    # respondAmount = min(SPres * (R - Ignore), SPResMax)
    b.add_component("kitControl:Subtract", "ExcessRequests")
    b.add_link("TotalRequests", "out", "ExcessRequests", "inA")
    b.add_link("Ignore", "out", "ExcessRequests", "inB")

    b.add_component("kitControl:Multiply", "ProportionalResponse")
    b.add_link("ExcessRequests", "out", "ProportionalResponse", "inA")
    b.add_link("SPres", "out", "ProportionalResponse", "inB")

    b.add_component("kitControl:Minimum", "CappedResponse")
    b.add_link("ProportionalResponse", "out", "CappedResponse", "inA")
    b.add_link("SPResMax", "out", "CappedResponse", "inB")

    # --- Select Trim or Respond adjustment value ---
    b.add_numeric_switch("Adjustment_Switch")
    b.add_link("IsRespondCondition", "out", "Adjustment_Switch", "inSwitch")
    b.add_link("CappedResponse", "out", "Adjustment_Switch", "inTrue")  # Respond
    b.add_link("SPtrim", "out", "Adjustment_Switch", "inFalse")       # Trim

    # --- Calculate the new setpoint ---
    b.add_component("kitControl:Add", "NewSetpoint_Unclamped")
    b.add_link("CurrentSp_Latch", "out", "NewSetpoint_Unclamped", "inA")
    b.add_link("Adjustment_Switch", "out", "NewSetpoint_Unclamped", "inB")
    b.end_sub_folder()

    # ==========================================================================
    # 5. OUTPUT CLAMPING AND SELECTION
    # This final stage clamps the calculated setpoint between SPmin and SPmax,
    # and selects between SP0 and the calculated SP based on the run state.
    # ==========================================================================
    b.start_sub_folder("OutputLogic")

    # Clamp the new setpoint: max(SPmin, min(NewSetpoint, SPmax))
    b.add_component("kitControl:Minimum", "Clamp_Hi")
    b.add_link("NewSetpoint_Unclamped", "out", "Clamp_Hi", "inA")
    b.add_link("SPmax", "out", "Clamp_Hi", "inB")

    b.add_component("kitControl:Maximum", "Clamp_Lo")
    b.add_link("Clamp_Hi", "out", "Clamp_Lo", "inA")
    b.add_link("SPmin", "out", "Clamp_Lo", "inB")

    # This is the final calculated Trim & Respond setpoint
    b.add_numeric_writable("CalculatedSp")
    b.add_link("Clamp_Lo", "out", "CalculatedSp", "in16")

    # The latch is updated only when the main logic and update trigger are active
    b.add_component("kitControl:And", "UpdateLatch_Clock")
    b.add_link("RunLogicEnable", "out", "UpdateLatch_Clock", "inA")
    b.add_link("UpdateTrigger", "out", "UpdateLatch_Clock", "inB")
    b.add_link("CalculatedSp", "out", "CurrentSp_Latch", "in")
    b.add_link("UpdateLatch_Clock", "out", "CurrentSp_Latch", "clock")

    # Final Mux: If RunLogic is enabled, use the latched SP. Otherwise, use SP0.
    b.add_numeric_switch("FinalSp_Switch")
    b.add_link("RunLogicEnable", "out", "FinalSp_Switch", "inSwitch")
    b.add_link("CurrentSp_Latch", "out", "FinalSp_Switch", "inTrue")
    b.add_link("SP0", "out", "FinalSp_Switch", "inFalse")
    b.end_sub_folder()

    # ==========================================================================
    # 6. FINAL WIRING
    # Connect the final selected setpoint to the main output.
    # ==========================================================================
    b.add_link("FinalSp_Switch", "out", "DischargeAirPressureSp_Out", "in16")


def main() -> None:
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Build a .bog file for the G36 Trim & Respond algorithm."
    )
    parser.add_argument(
        "-o",
        "--output_dir",
        default="examples",
        help="Directory to write the .bog file.",
    )
    args = parser.parse_args()

    builder = BogFolderBuilder("G36_AHU_Duct_Static_Reset")
    build_graph(builder)

    os.makedirs(args.output_dir, exist_ok=True)
    out_path = os.path.join(args.output_dir, "hvac_g36_ahu_duct_static_reset.bog")
    builder.save(out_path)
    print(f"Successfully created Niagara .bog file at: {os.path.abspath(out_path)}")


if __name__ == "__main__":
    main()
