

"""
Prompt:
Can you attempt a working pump lead lag example and also add in a PID for 
differential pressure control on the pump speed to a setpoint of 20 PSI. 
Pretend its a heat plant where we need to see outside air temperature 
and a setpoint to enabled the plant below 50F with hysterious where then 
pump single pump starts to control to different pressure setpoint and 
if a pump fails because there is 2 of them it will switch automatocally
 to the other after a 1 minute timer experies where we should also 
 have a bool point for an alarm as well. 

hvac_pump_lead_lag_dp_pid.py

Dual-pump lead/lag with failure takeover + DP PID speed control.
Plant enables below an OAT enable setpoint with hysteresis (no latch):
  - Start when OAT <= OAT_Enable_SP
  - Stop  when OAT >= OAT_Enable_SP + DB_Deadband

Lead/lag:
  - User selects lead pump (LeadIsPump1).
  - If designated lead is not running for 5s and remains failed for 60s,
    auto-transfer to the lag pump.

DP control:
  - kitControl:LoopPoint drives PumpSpeedCmd to DP_SP (default 20 PSI).

Only one CLI arg: -o / --output_dir
"""

from __future__ import annotations

import argparse
import os
import sys

# Project import convention (same as your examples)
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))
from bog_builder import BogFolderBuilder  # noqa: E402


FOLDER_NAME = "HeatPlant_LeadLag_DP"
BOG_NAME = "hvac_pump_lead_lag_dp_pid.bog"


def build_graph(b: BogFolderBuilder) -> None:
    # =======================
    # Top-level I/O and SPs
    # =======================
    # Sensors
    b.add_numeric_writable("OAT", default_value=55.0)                    # °F
    b.add_numeric_writable("DifferentialPressure", default_value=18.0)   # PSI

    # Enable setpoint + single deadband (no latch hysteresis)
    b.add_numeric_writable("OAT_Enable_SP", default_value=50.0)          # °F start threshold
    b.add_component("kitControl:NumericConst", "DB_Deadband", properties={"value": 2.0})  # °F

    # DP loop setpoint and general knobs
    b.add_numeric_writable("DP_SP", default_value=20.0)            # PSI
    b.add_boolean_writable("EnableCmd", default_value=True)        # operator enable gate
    b.add_boolean_writable("LeadIsPump1", default_value=True)      # user lead selection

    # Timers (ms)
    b.add_numeric_writable("FailConfirm_ms", default_value=5000.0)   # confirm not-running
    b.add_numeric_writable("SwapDelay_ms",  default_value=60000.0)   # delay before swap

    # Status inputs (feedbacks)
    b.add_boolean_writable("Pump1_Status", default_value=False)
    b.add_boolean_writable("Pump2_Status", default_value=False)

    # Outputs
    b.add_boolean_writable("Pump1_Cmd")
    b.add_boolean_writable("Pump2_Cmd")
    b.add_numeric_writable("PumpSpeedCmd")   # 0..100 %
    b.add_boolean_writable("LeadFailAlarm")

    # =======================
    # Plant enable (Schmitt w/out latch)
    # =======================
    b.start_sub_folder("PlantEnable")

    # SP + DB → Stop threshold
    b.add_component("kitControl:Add", "SP_Plus_DB")
    b.add_link("OAT_Enable_SP", "out", "SP_Plus_DB", "inA")
    b.add_link("DB_Deadband",  "out", "SP_Plus_DB", "inB")

    # Comparators
    b.add_component("kitControl:LessThanEqual",    "LE_Start")  # OAT ≤ SP
    b.add_component("kitControl:GreaterThanEqual", "GE_Stop")   # OAT ≥ SP+DB
    b.add_link("OAT",           "out", "LE_Start", "inA")
    b.add_link("OAT_Enable_SP", "out", "LE_Start", "inB")
    b.add_link("OAT",           "out", "GE_Stop",  "inA")
    b.add_link("SP_Plus_DB",    "out", "GE_Stop",  "inB")

    # Memory of previous enable using BooleanDelay (tiny hold)
    b.add_component("kitControl:BooleanDelay", "PrevEnable", properties={"onDelay": "10", "offDelay": "10"})

    # (PrevEnable AND NOT Stop) OR Start
    b.add_component("kitControl:Not", "Not_Stop")
    b.add_component("kitControl:And", "Prev_AND_NotStop")
    b.add_component("kitControl:Or",  "Enable_OR")
    b.add_link("GE_Stop", "out", "Not_Stop", "in")
    b.add_link("PrevEnable", "out", "Prev_AND_NotStop", "inA")
    b.add_link("Not_Stop",   "out", "Prev_AND_NotStop", "inB")
    b.add_link("Prev_AND_NotStop", "out", "Enable_OR", "inA")
    b.add_link("LE_Start",          "out", "Enable_OR", "inB")

    # Close the loop for the memory
    b.add_link("Enable_OR", "out", "PrevEnable", "in")

    # Export PlantEnable as a writable for visibility
    b.add_boolean_writable("PlantEnable")
    b.add_link("Enable_OR", "out", "PlantEnable", "in16")

    b.end_sub_folder()

    # Gate with operator EnableCmd
    b.start_sub_folder("EnableGate")
    b.add_component("kitControl:And", "PlantEnabled_AND")
    b.add_link("PlantEnable", "out", "PlantEnabled_AND", "inA")
    b.add_link("EnableCmd",   "out", "PlantEnabled_AND", "inB")
    b.end_sub_folder()

    # =======================
    # Lead/Lag & Failure logic
    # =======================
    b.start_sub_folder("LeadLag")

    # Lead selection to boolean
    b.add_component("kitControl:Equal", "LeadIsP1_Bool")
    b.add_component("kitControl:NumericConst", "ONE",  properties={"value": 1.0})
    b.add_component("kitControl:NumericConst", "ZERO", properties={"value": 0.0})
    b.add_link("LeadIsPump1", "out", "LeadIsP1_Bool", "inA")
    b.add_link("ONE",         "out", "LeadIsP1_Bool", "inB")

    # Complements / status
    b.add_component("kitControl:Not", "LeadIsP2_Bool")
    b.add_link("LeadIsP1_Bool", "out", "LeadIsP2_Bool", "in")
    b.add_component("kitControl:Not", "Not_P1_Status")
    b.add_component("kitControl:Not", "Not_P2_Status")
    b.add_link("Pump1_Status", "out", "Not_P1_Status", "in")
    b.add_link("Pump2_Status", "out", "Not_P2_Status", "in")

    # Confirm "lead not running" for 5s
    b.add_component("kitControl:And", "P1_LeadAndNotRunning")
    b.add_component("kitControl:And", "P2_LeadAndNotRunning")
    b.add_link("LeadIsP1_Bool", "out", "P1_LeadAndNotRunning", "inA")
    b.add_link("Not_P1_Status", "out", "P1_LeadAndNotRunning", "inB")
    b.add_link("LeadIsP2_Bool", "out", "P2_LeadAndNotRunning", "inA")
    b.add_link("Not_P2_Status", "out", "P2_LeadAndNotRunning", "inB")

    b.add_component("kitControl:BooleanDelay", "P1_FailConfirm", properties={"onDelay": "5000",  "offDelay": "0"})
    b.add_component("kitControl:BooleanDelay", "P2_FailConfirm", properties={"onDelay": "5000",  "offDelay": "0"})
    b.add_link("P1_LeadAndNotRunning", "out", "P1_FailConfirm", "in")
    b.add_link("P2_LeadAndNotRunning", "out", "P2_FailConfirm", "in")

    # Add 60s swap delay
    b.add_component("kitControl:BooleanDelay", "SwapAfterP1Fail", properties={"onDelay": "60000", "offDelay": "0"})
    b.add_component("kitControl:BooleanDelay", "SwapAfterP2Fail", properties={"onDelay": "60000", "offDelay": "0"})
    b.add_link("P1_FailConfirm", "out", "SwapAfterP1Fail", "in")
    b.add_link("P2_FailConfirm", "out", "SwapAfterP2Fail", "in")

    # Command logic when P1 is lead
    b.add_numeric_switch("P1_Cmd_when_P1Lead")
    b.add_numeric_switch("P2_Cmd_when_P1Lead")
    b.add_link("SwapAfterP1Fail", "out", "P1_Cmd_when_P1Lead", "inSwitch")
    b.add_link("ZERO", "out", "P1_Cmd_when_P1Lead", "inTrue")    # failed → P1 OFF
    b.add_link("ONE",  "out", "P1_Cmd_when_P1Lead", "inFalse")   # OK     → P1 ON

    b.add_link("SwapAfterP1Fail", "out", "P2_Cmd_when_P1Lead", "inSwitch")
    b.add_link("ONE",  "out", "P2_Cmd_when_P1Lead", "inTrue")    # failed → P2 ON
    b.add_link("ZERO", "out", "P2_Cmd_when_P1Lead", "inFalse")   # OK     → P2 OFF

    # Command logic when P2 is lead
    b.add_numeric_switch("P1_Cmd_when_P2Lead")
    b.add_numeric_switch("P2_Cmd_when_P2Lead")
    b.add_link("SwapAfterP2Fail", "out", "P1_Cmd_when_P2Lead", "inSwitch")
    b.add_link("ONE",  "out", "P1_Cmd_when_P2Lead", "inTrue")    # failed → P1 ON
    b.add_link("ZERO", "out", "P1_Cmd_when_P2Lead", "inFalse")   # OK     → P1 OFF

    b.add_link("SwapAfterP2Fail", "out", "P2_Cmd_when_P2Lead", "inSwitch")
    b.add_link("ZERO", "out", "P2_Cmd_when_P2Lead", "inTrue")    # failed → P2 OFF
    b.add_link("ONE",  "out", "P2_Cmd_when_P2Lead", "inFalse")   # OK     → P2 ON

    # Select final commands by lead selection
    b.add_numeric_switch("P1_Final_CmdNum")
    b.add_numeric_switch("P2_Final_CmdNum")
    b.add_link("LeadIsP1_Bool", "out", "P1_Final_CmdNum", "inSwitch")
    b.add_link("P1_Cmd_when_P1Lead", "out", "P1_Final_CmdNum", "inTrue")
    b.add_link("P1_Cmd_when_P2Lead", "out", "P1_Final_CmdNum", "inFalse")

    b.add_link("LeadIsP1_Bool", "out", "P2_Final_CmdNum", "inSwitch")
    b.add_link("P2_Cmd_when_P1Lead", "out", "P2_Final_CmdNum", "inTrue")
    b.add_link("P2_Cmd_when_P2Lead", "out", "P2_Final_CmdNum", "inFalse")

    # Gate by PlantEnabled_AND
    b.add_numeric_switch("P1_Final_Gated")
    b.add_numeric_switch("P2_Final_Gated")
    b.add_link("PlantEnabled_AND", "out", "P1_Final_Gated", "inSwitch")
    b.add_link("P1_Final_CmdNum", "out", "P1_Final_Gated", "inTrue")
    b.add_link("ZERO", "out", "P1_Final_Gated", "inFalse")

    b.add_link("PlantEnabled_AND", "out", "P2_Final_Gated", "inSwitch")
    b.add_link("P2_Final_CmdNum", "out", "P2_Final_Gated", "inTrue")
    b.add_link("ZERO", "out", "P2_Final_Gated", "inFalse")

    # Lead-fail alarm
    b.add_component("kitControl:And", "P1_LeadFailActive")
    b.add_component("kitControl:And", "P2_LeadFailActive")
    b.add_link("LeadIsP1_Bool", "out", "P1_LeadFailActive", "inA")
    b.add_link("SwapAfterP1Fail", "out", "P1_LeadFailActive", "inB")
    b.add_link("LeadIsP2_Bool", "out", "P2_LeadFailActive", "inA")
    b.add_link("SwapAfterP2Fail", "out", "P2_LeadFailActive", "inB")

    b.add_component("kitControl:Or", "LeadFail_OR")
    b.add_link("P1_LeadFailActive", "out", "LeadFail_OR", "inA")
    b.add_link("P2_LeadFailActive", "out", "LeadFail_OR", "inB")

    b.end_sub_folder()

    # =======================
    # DP PID speed control
    # =======================
    b.start_sub_folder("DPPID")

    # LoopPoint (Reverse action typical for DP control: PV below SP → output increases)
    b.add_component("kitControl:LoopPoint", "DP_Loop")

    # PI gains and action
    b.add_component("kitControl:NumericConst", "Kp",      properties={"value": 1.5})
    b.add_component("kitControl:NumericConst", "Ki",      properties={"value": 0.2})
    b.add_component("kitControl:NumericConst", "Reverse", properties={"value": 0.0})  # 0=Reverse, 1=Direct

    # Wire
    b.add_link("PlantEnabled_AND",     "out", "DP_Loop", "loopEnable")
    b.add_link("DifferentialPressure", "out", "DP_Loop", "controlledVariable")
    b.add_link("DP_SP",                "out", "DP_Loop", "setpoint")
    b.add_link("Reverse",              "out", "DP_Loop", "loopAction")
    b.add_link("Kp",                   "out", "DP_Loop", "proportionalConstant")
    b.add_link("Ki",                   "out", "DP_Loop", "integralConstant")

    # Gate PID out by enable (0 when disabled)
    b.add_numeric_switch("Speed_Gated")
    b.add_component("kitControl:NumericConst", "ZERO_SPEED", properties={"value": 0.0})
    b.add_link("PlantEnabled_AND", "out", "Speed_Gated", "inSwitch")
    b.add_link("DP_Loop",         "out", "Speed_Gated", "inTrue")
    b.add_link("ZERO_SPEED",      "out", "Speed_Gated", "inFalse")

    b.end_sub_folder()

    # =======================
    # Final top-level links
    # =======================
    b.add_link("P1_Final_Gated", "out", "Pump1_Cmd", "in16")
    b.add_link("P2_Final_Gated", "out", "Pump2_Cmd", "in16")
    b.add_link("Speed_Gated",    "out", "PumpSpeedCmd", "in16")
    b.add_link("LeadFail_OR",    "out", "LeadFailAlarm", "in16")


def main() -> None:
    p = argparse.ArgumentParser(description="Generate pump lead/lag + DP PID .bog")
    p.add_argument("-o", "--output_dir", default="examples", help="Output directory for .bog")
    args = p.parse_args()

    b = BogFolderBuilder(FOLDER_NAME, debug=True)
    build_graph(b)

    os.makedirs(args.output_dir, exist_ok=True)
    out_path = os.path.join(args.output_dir, BOG_NAME)
    b.save(out_path)
    print(f"Created Niagara .bog at: {os.path.abspath(out_path)}")


if __name__ == "__main__":
    main()
