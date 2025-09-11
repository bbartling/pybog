"""
Combines a simple Tstat-based plant enable with advanced multi-stage,
runtime-based sequencing for a three-chiller, three-pump central plant.
"""

import os
import argparse
from bog_builder import BogFolderBuilder


def main():
    """
    Builds the advanced chiller plant .bog file.
    """
    parser = argparse.ArgumentParser(
        description="Build a .bog file for an advanced chiller plant."
    )
    parser.add_argument(
        "-o",
        "--output_dir",
        default="examples",
        help="Output directory for the .bog file.",
    )
    args = parser.parse_args()

    builder = BogFolderBuilder("AdvancedChillerPlant", debug=True)

    # --- Configuration ---
    NUM_EQUIPMENT = 3
    CHILLER_MAX_RUNTIME = "200h"
    PUMP_MAX_RUNTIME = "200h"
    TIMER_PERIOD_MS = "1000"  # 1 second pulse

    print("--- Creating Top-Level Inputs & Outputs ---")

    # --- Inputs ---
    builder.add_numeric_writable("Outside_Air_Temperature", default_value=75.0)
    builder.add_numeric_writable("Chiller_Demand", default_value=0.0)

    chiller_names = [f"Chiller_{i+1}" for i in range(NUM_EQUIPMENT)]
    pump_names = [f"Pump_{i+1}" for i in range(NUM_EQUIPMENT)]
    all_equipment_names = chiller_names + pump_names

    # CORRECTED: Create pump status points with letter names (A, B, C) to match linking logic
    for i in range(NUM_EQUIPMENT):
        slot_letter = chr(ord("A") + i)
        builder.add_boolean_writable(f"Pump_{slot_letter}_Status", default_value=False)

    # --- Outputs ---
    for name in all_equipment_names:
        builder.add_boolean_writable(f"{name}_Cmd", default_value=False)
        builder.add_numeric_writable(f"{name}_Runtime_Seconds", default_value=0.0)

    builder.add_numeric_writable("Total_Chillers_Running", default_value=0.0)

    print("\n--- Creating Logic Components inside 'Logic' sub-folder ---")
    builder.start_sub_folder("Logic")

    # --- Master Plant Enable ---
    builder.add_tstat("Plant_Enable_Tstat")
    builder.add_numeric_const("Enable_Setpoint", value=60.0)
    builder.add_numeric_const("Enable_Differential", value=2.0)
    builder.add_boolean_const(
        "Enable_Action_Direct", value=True
    )  # True for direct-acting enable

    # --- Staging & Rotation Blocks ---
    builder.add_lead_lag_runtime(
        "Chiller_LeadLag",
        properties={"numberOutputs": NUM_EQUIPMENT, "maxRuntime": CHILLER_MAX_RUNTIME},
    )
    builder.add_lead_lag_runtime(
        "Pump_LeadLag",
        properties={"numberOutputs": NUM_EQUIPMENT, "maxRuntime": PUMP_MAX_RUNTIME},
    )

    # --- Staging Logic ---
    # Convert numeric demand into boolean stage requests
    for i in range(1, NUM_EQUIPMENT + 1):
        builder.add_greater_than_equal(f"Chiller_Stage_{i}_Req_Check")
        builder.add_numeric_const(f"Const_{i}", value=float(i))
        builder.add_and(f"Chiller_Stage_{i}_Req")

    # --- Runtime Accumulation & Latching ---
    builder.add_multi_vibrator("One_Second_Timer", period_ms=TIMER_PERIOD_MS)
    builder.add_one_shot("Timer_Pulse")
    builder.add_numeric_const("Increment_Value", value=1.0)
    for name in all_equipment_names:
        builder.add_counter(f"{name}_RuntimeCounter")
        builder.add_and(f"{name}_IncrementGate")
        builder.add_numeric_latch(f"{name}_RuntimeLatch")
        builder.add_not(f"{name}_Cmd_Off_Detector")

    # --- Pump Demand Interlock ---
    builder.add_add("Sum_Running_Chillers")
    for name in chiller_names:
        builder.add_numeric_switch(f"{name}_BoolToNum")
    builder.add_numeric_const("Const_1_Num", value=1.0)
    for i in range(1, NUM_EQUIPMENT + 1):
        builder.add_greater_than_equal(f"Pump_Stage_{i}_Req_Check")
        builder.add_and(f"Pump_Stage_{i}_Req")

    # --- Feedback Logic ---
    builder.add_or("Chiller_Feedback_Or")
    builder.add_or("Pump_Feedback_Or")

    builder.end_sub_folder()

    print("\n--- Wiring Components ---")

    # --- 1. Wire Master Enable ---
    builder.add_link("Outside_Air_Temperature", "out", "Plant_Enable_Tstat", "cv")
    builder.add_link("Enable_Setpoint", "out", "Plant_Enable_Tstat", "sp")
    builder.add_link("Enable_Differential", "out", "Plant_Enable_Tstat", "diff")
    builder.add_link(
        "Enable_Action_Direct",
        "out",
        "Plant_Enable_Tstat",
        "action",
        link_type="b:ConversionLink",
        converter_type="conv:StatusBooleanToFrozenEnum",
    )

    # --- 2. Wire Chiller Staging and Rotation ---
    builder.add_link("Plant_Enable_Tstat", "out", "Chiller_LeadLag", "in")
    for i in range(1, NUM_EQUIPMENT + 1):
        builder.add_link("Chiller_Demand", "out", f"Chiller_Stage_{i}_Req_Check", "inA")
        builder.add_link(f"Const_{i}", "out", f"Chiller_Stage_{i}_Req_Check", "inB")
        builder.add_link(
            f"Chiller_Stage_{i}_Req_Check", "out", f"Chiller_Stage_{i}_Req", "inA"
        )
        builder.add_link("Plant_Enable_Tstat", "out", f"Chiller_Stage_{i}_Req", "inB")

    # --- 3. Wire Pump Demand Interlock & Staging ---
    builder.add_link("Plant_Enable_Tstat", "out", "Pump_LeadLag", "in")
    for i, name in enumerate(chiller_names):
        slot = chr(ord("A") + i)
        builder.add_link(f"{name}_Cmd", "out", f"{name}_BoolToNum", "inSwitch")
        builder.add_link("Const_1_Num", "out", f"{name}_BoolToNum", "inTrue")
        builder.add_link(
            f"{name}_BoolToNum", "out", "Sum_Running_Chillers", f"in{slot}"
        )
    builder.add_link("Sum_Running_Chillers", "out", "Total_Chillers_Running", "in16")

    for i in range(1, NUM_EQUIPMENT + 1):
        builder.add_link(
            "Sum_Running_Chillers", "out", f"Pump_Stage_{i}_Req_Check", "inA"
        )
        builder.add_link(f"Const_{i}", "out", f"Pump_Stage_{i}_Req_Check", "inB")
        builder.add_link(
            f"Pump_Stage_{i}_Req_Check", "out", f"Pump_Stage_{i}_Req", "inA"
        )
        builder.add_link("Plant_Enable_Tstat", "out", f"Pump_Stage_{i}_Req", "inB")

    # --- 4. Wire Master Timer ---
    builder.add_link("One_Second_Timer", "out", "Timer_Pulse", "in")

    # --- 5. Wire Final Commands and Runtime Logic for All Equipment ---
    equip_map = {
        "A": (chiller_names[0], pump_names[0]),
        "B": (chiller_names[1], pump_names[1]),
        "C": (chiller_names[2], pump_names[2]),
    }
    for i, (slot, (chiller_name, pump_name)) in enumerate(equip_map.items()):
        stage = i + 1
        # Chiller Command and Runtime
        builder.add_and(f"{chiller_name}_Cmd_Gate")
        builder.add_link(
            f"Chiller_Stage_{stage}_Req", "out", f"{chiller_name}_Cmd_Gate", "inA"
        )
        builder.add_link(
            f"Chiller_LeadLag", f"out{slot}", f"{chiller_name}_Cmd_Gate", "inB"
        )
        builder.add_link(
            f"{chiller_name}_Cmd_Gate", "out", f"{chiller_name}_Cmd", "in16"
        )

        # Pump Command and Runtime
        builder.add_and(f"{pump_name}_Cmd_Gate")
        builder.add_link(
            f"Pump_Stage_{stage}_Req", "out", f"{pump_name}_Cmd_Gate", "inA"
        )
        builder.add_link(f"Pump_LeadLag", f"out{slot}", f"{pump_name}_Cmd_Gate", "inB")
        builder.add_link(f"{pump_name}_Cmd_Gate", "out", f"{pump_name}_Cmd", "in16")

    for name in all_equipment_names:
        # Runtime Accumulation
        builder.add_link("Timer_Pulse", "out", f"{name}_IncrementGate", "inA")
        builder.add_link(f"{name}_Cmd", "out", f"{name}_IncrementGate", "inB")
        builder.add_link(
            f"{name}_IncrementGate", "out", f"{name}_RuntimeCounter", "countUp"
        )
        builder.add_link(
            "Increment_Value", "out", f"{name}_RuntimeCounter", "countIncrement"
        )
        builder.add_link(
            f"{name}_RuntimeCounter", "out", f"{name}_Runtime_Seconds", "in16"
        )
        # Runtime Latching
        builder.add_link(f"{name}_RuntimeCounter", "out", f"{name}_RuntimeLatch", "in")
        builder.add_link(f"{name}_Cmd", "out", f"{name}_Cmd_Off_Detector", "in")
        builder.add_link(
            f"{name}_Cmd_Off_Detector", "out", f"{name}_RuntimeLatch", "clock"
        )

    # --- 6. Wire Feedback and Runtime to LeadLag blocks ---
    for slot, (chiller_name, pump_name) in equip_map.items():
        # Feedback
        builder.add_link(
            f"{chiller_name}_Cmd", "out", "Chiller_Feedback_Or", f"in{slot}"
        )
        builder.add_link(f"Pump_{slot}_Status", "out", "Pump_Feedback_Or", f"in{slot}")
        # Runtime
        builder.add_link(
            f"{chiller_name}_RuntimeLatch",
            "out",
            "Chiller_LeadLag",
            f"runtime{slot}",
            link_type="b:ConversionLink",
            converter_type="conv:StatusNumericToRelTime",
        )
        builder.add_link(
            f"{pump_name}_RuntimeLatch",
            "out",
            "Pump_LeadLag",
            f"runtime{slot}",
            link_type="b:ConversionLink",
            converter_type="conv:StatusNumericToRelTime",
        )

    builder.add_link("Chiller_Feedback_Or", "out", "Chiller_LeadLag", "feedback")
    builder.add_link("Pump_Feedback_Or", "out", "Pump_LeadLag", "feedback")

    # --- Save the .bog file ---
    bog_filename = "hvac_simple_chiller_plant_two.bog"
    output_path = os.path.join(args.output_dir, bog_filename)
    os.makedirs(args.output_dir, exist_ok=True)
    builder.save(output_path)
    print(
        f"\nSuccessfully created Niagara .bog file at: {os.path.abspath(output_path)}"
    )


if __name__ == "__main__":
    main()
