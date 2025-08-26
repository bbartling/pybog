"""
hvac_g36_ahu_duct_static_reset_updated.py

Enhanced G36 Duct Static Pressure Trim & Respond builder with:
1) UpdateMinutes dynamically wired to the MultiVibrator Period
2) StartUpDelayMinutes converted to ms and (best-effort) wired to BooleanDelay OnDelay
3) True slew-rate limiting using SPResMax as the max absolute change per update tick
   (symmetric clamp for both TRIM and RESPOND)

Notes:
- In Niagara Workbench, some timer components do not accept live period updates over a link;
  however, the link is provided for correctness/documentation and initial value is honored.
- The symmetric clamp mirrors the "rate_of_change_limiter" pattern: the per-cycle adjustment
  is limited to ±SPResMax then added to the previous latched setpoint.
"""

from __future__ import annotations
import argparse
import os
import sys

# Append project src directory to path for bog_builder import
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))
from bog_builder import BogFolderBuilder


def build_g36_graph(b: BogFolderBuilder) -> None:
    """Builds the G36 Trim & Respond logic graph (enhanced)."""

    # ==========================================================================
    # 1) TOP-LEVEL I/O AND CONFIGURATION
    # ==========================================================================
    b.add_boolean_writable("FanRunCmd", default_value=False)
    b.add_numeric_writable("TotalRequests", default_value=0.0, precision=0)
    b.add_numeric_writable(
        "DischargeAirPressureSp_Out",
        default_value=1.25,
        precision=2,
        units="u:inchesOfWater",
    )

    # Configuration setpoints
    sp0_default = 1.25
    b.add_numeric_writable("SP0", default_value=sp0_default, units="u:inchesOfWater")
    b.add_numeric_writable(
        "SPmin", default_value=0.40, precision=2, units="u:inchesOfWater"
    )
    b.add_numeric_writable(
        "SPmax", default_value=1.25, precision=2, units="u:inchesOfWater"
    )

    startup_delay_default_min = 0.5
    b.add_numeric_writable(
        "StartUpDelayMinutes", default_value=startup_delay_default_min
    )

    update_cadence_default_min = 0.5
    b.add_numeric_writable("UpdateMinutes", default_value=update_cadence_default_min)

    b.add_numeric_writable("Ignore", default_value=1.0, precision=0)
    b.add_numeric_writable(
        "SPtrim", default_value=-0.02, precision=2, units="u:inchesOfWater"
    )
    b.add_numeric_writable(
        "SPres", default_value=0.04, precision=2, units="u:inchesOfWater"
    )
    # SPResMax acts as a *rate-of-change limit* per update interval (both directions)
    b.add_numeric_writable(
        "SPResMax", default_value=0.08, precision=2, units="u:inchesOfWater"
    )

    # ==========================================================================
    # 2) STATE MANAGEMENT + STARTUP DELAY
    # ==========================================================================
    b.start_sub_folder("StateManagement")

    # Latch rising edge of fan run to kick off startup sequencing
    b.add_component("kitControl:BooleanLatch", "FanRunLatch")
    b.add_component("kitControl:Not", "Not_FanRun")
    b.add_link("FanRunCmd", "out", "FanRunLatch", "clock")
    b.add_link("FanRunCmd", "out", "Not_FanRun", "in")
    b.add_link("Not_FanRun", "out", "FanRunLatch", "in")

    # BooleanDelay for startup (initial onDelay from default minutes)
    startup_delay_ms = str(int(startup_delay_default_min * 60000))
    b.add_component(
        "kitControl:BooleanDelay",
        "StartupDelayTimer",
        properties={"onDelay": startup_delay_ms},
    )
    b.add_link("FanRunLatch", "out", "StartupDelayTimer", "in")

    # Show StartUpDelayMinutes converted to ms and best-effort wire to OnDelay
    b.add_component(
        "kitControl:NumericConst", "Const_60000_A", properties={"value": 60000.0}
    )
    b.add_component("kitControl:Multiply", "StartupDelay_ms_Display")
    b.add_numeric_writable("CalculatedStartupDelay_ms")
    b.add_link("StartUpDelayMinutes", "out", "StartupDelay_ms_Display", "inA")
    b.add_link("Const_60000_A", "out", "StartupDelay_ms_Display", "inB")
    b.add_link("StartupDelay_ms_Display", "out", "CalculatedStartupDelay_ms", "in16")
    # Some Niagara builds may not allow dynamic linking into config slots, but we link for clarity
    b.add_link("CalculatedStartupDelay_ms", "out", "StartupDelayTimer", "onDelay")

    # Enable core logic only when fan is running AND startup delay is satisfied
    b.add_component("kitControl:And", "RunLogicEnable")
    b.add_link("FanRunCmd", "out", "RunLogicEnable", "inA")
    b.add_link("StartupDelayTimer", "out", "RunLogicEnable", "inB")
    b.end_sub_folder()

    # ==========================================================================
    # 3) PERIODIC UPDATE TIMER (cadence)
    # ==========================================================================
    b.start_sub_folder("UpdateTimer")

    # MultiVibrator with initial period from default minutes; pulses are one-shot'd
    update_cadence_ms = str(int(update_cadence_default_min * 60000))
    b.add_component(
        "kitControl:MultiVibrator",
        "UpdatePulse",
        properties={"period": update_cadence_ms},
    )
    b.add_component("kitControl:OneShot", "UpdateTrigger")
    b.add_link("UpdatePulse", "out", "UpdateTrigger", "in")

    # Show UpdateMinutes converted to ms and wire to the MultiVibrator Period
    b.add_component(
        "kitControl:NumericConst", "Const_60000_B", properties={"value": 60000.0}
    )
    b.add_component("kitControl:Multiply", "UpdateCadence_ms_Display")
    b.add_numeric_writable("CalculatedUpdateCadence_ms")
    b.add_link("UpdateMinutes", "out", "UpdateCadence_ms_Display", "inA")
    b.add_link("Const_60000_B", "out", "UpdateCadence_ms_Display", "inB")
    b.add_link("UpdateCadence_ms_Display", "out", "CalculatedUpdateCadence_ms", "in16")
    b.add_link("CalculatedUpdateCadence_ms", "out", "UpdatePulse", "Period")

    b.end_sub_folder()

    # ==========================================================================
    # 4) TRIM/RESPOND WITH RATE LIMIT (per UpdateTrigger)
    # ==========================================================================
    b.start_sub_folder("TrimRespondLogic")

    # Memory: current effective setpoint; seed with SP0 to avoid big first jump
    b.add_component(
        "kitControl:NumericLatch",
        "CurrentSp_Latch",
        properties={"out": {"value": sp0_default}},
    )

    # Are we in a RESPOND condition?
    b.add_component("kitControl:GreaterThan", "IsRespondCondition")
    b.add_link("TotalRequests", "out", "IsRespondCondition", "inA")
    b.add_link("Ignore", "out", "IsRespondCondition", "inB")

    # RESPOND amount = SPres * max(0, TotalRequests - Ignore)
    b.add_component("kitControl:Subtract", "ExcessRequests")
    b.add_link("TotalRequests", "out", "ExcessRequests", "inA")
    b.add_link("Ignore", "out", "ExcessRequests", "inB")

    b.add_component("kitControl:Multiply", "ProportionalResponse")
    b.add_link("ExcessRequests", "out", "ProportionalResponse", "inA")
    b.add_link("SPres", "out", "ProportionalResponse", "inB")

    # Select TRIM vs RESPOND raw adjustment
    b.add_numeric_switch("DesiredAdjustment_Switch")
    b.add_link("IsRespondCondition", "out", "DesiredAdjustment_Switch", "inSwitch")
    b.add_link("ProportionalResponse", "out", "DesiredAdjustment_Switch", "inTrue")
    b.add_link("SPtrim", "out", "DesiredAdjustment_Switch", "inFalse")

    # --- SLEW-RATE LIMIT: clamp desired adjustment to ±SPResMax per update tick
    b.add_component(
        "kitControl:NumericConst", "Const_Neg_1", properties={"value": -1.0}
    )
    b.add_component("kitControl:Multiply", "Neg_SPResMax")
    b.add_component("kitControl:Maximum", "ClampLow")
    b.add_component("kitControl:Minimum", "ClampHigh")

    b.add_link("SPResMax", "out", "Neg_SPResMax", "inA")
    b.add_link("Const_Neg_1", "out", "Neg_SPResMax", "inB")
    b.add_link("DesiredAdjustment_Switch", "out", "ClampLow", "inA")
    b.add_link("Neg_SPResMax", "out", "ClampLow", "inB")
    b.add_link("ClampLow", "out", "ClampHigh", "inA")
    b.add_link("SPResMax", "out", "ClampHigh", "inB")

    # New (unclamped) setpoint uses the rate-limited adjustment
    b.add_component("kitControl:Add", "NewSetpoint_Unclamped")
    b.add_link("CurrentSp_Latch", "out", "NewSetpoint_Unclamped", "inA")
    b.add_link("ClampHigh", "out", "NewSetpoint_Unclamped", "inB")

    b.end_sub_folder()

    # ==========================================================================
    # 5) OUTPUT CLAMPING + LATCHED UPDATE
    # ==========================================================================
    b.start_sub_folder("OutputLogic")

    # Clamp to [SPmin, SPmax]
    b.add_component("kitControl:Minimum", "Clamp_Hi")
    b.add_link("NewSetpoint_Unclamped", "out", "Clamp_Hi", "inA")
    b.add_link("SPmax", "out", "Clamp_Hi", "inB")

    b.add_component("kitControl:Maximum", "Clamp_Lo")
    b.add_link("Clamp_Hi", "out", "Clamp_Lo", "inA")
    b.add_link("SPmin", "out", "Clamp_Lo", "inB")

    b.add_numeric_writable("CalculatedSp")
    b.add_link("Clamp_Lo", "out", "CalculatedSp", "in16")

    # Latch updates only on UpdateTrigger AND RunLogicEnable
    b.add_component("kitControl:And", "UpdateLatch_Clock")
    b.add_link("RunLogicEnable", "out", "UpdateLatch_Clock", "inA")
    b.add_link("UpdateTrigger", "out", "UpdateLatch_Clock", "inB")
    b.add_link("CalculatedSp", "out", "CurrentSp_Latch", "in")
    b.add_link("UpdateLatch_Clock", "out", "CurrentSp_Latch", "clock")

    # Final mux: when not running / during startup, hold SP0
    b.add_numeric_switch("FinalSp_Switch")
    b.add_link("RunLogicEnable", "out", "FinalSp_Switch", "inSwitch")
    b.add_link("CurrentSp_Latch", "out", "FinalSp_Switch", "inTrue")
    b.add_link("SP0", "out", "FinalSp_Switch", "inFalse")

    b.end_sub_folder()

    # ==========================================================================
    # 6) FINAL WIRING
    # ==========================================================================
    b.add_link("FinalSp_Switch", "out", "DischargeAirPressureSp_Out", "in16")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a .bog for G36 Trim & Respond (enhanced)."
    )
    parser.add_argument(
        "-o",
        "--output_dir",
        default="examples",
        help="Directory to write the .bog file.",
    )
    args = parser.parse_args()

    builder = BogFolderBuilder("G36_AHU_Duct_Static_Reset")
    build_g36_graph(builder)

    output_filename = "hvac_g36_ahu_duct_static_reset.bog"
    os.makedirs(args.output_dir, exist_ok=True)
    out_path = os.path.join(args.output_dir, output_filename)
    builder.save(out_path)
    print(f"Created Niagara .bog at: {os.path.abspath(out_path)}")


if __name__ == "__main__":
    main()
