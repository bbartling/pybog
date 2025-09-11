import os, argparse
from bog_builder import BogFolderBuilder


def main():
    """
    Builds and saves a robust, clarified chiller plant staging logic .bog file.

    This definitive version (v3) separates the master enable signal (boolean) from
    the staging demand (numeric). It uses And gates on the final outputs to ensure
    the plant enable signal acts as a master interlock, which is a more robust
    and standard design pattern.

    It also retains the robust latching mechanism for runtime feedback from v2.
    """
    parser = argparse.ArgumentParser(
        description="Build a definitive .bog file for chiller staging logic."
    )
    parser.add_argument(
        "-o",
        "--output_dir",
        default="examples",
        help="Output directory for the .bog file.",
    )
    args = parser.parse_args()

    builder = BogFolderBuilder("cooling_plant_staging_v3", debug=True)

    print("--- Creating Top-Level Inputs & Outputs ---")

    # --- System Master Inputs ---
    builder.add_boolean_writable("Plant_Enable", default_value=False)
    builder.add_numeric_writable(
        "Chiller_Demand_Raw", default_value=0.0
    )  # 0-3 raw demand

    # --- Equipment Command & Runtime Outputs ---
    num_equipment = 3
    chiller_names = [f"Chiller_{i+1}" for i in range(num_equipment)]
    pump_names = [f"Pump_{i+1}" for i in range(num_equipment)]
    all_equipment_names = chiller_names + pump_names

    for name in all_equipment_names:
        builder.add_boolean_writable(f"{name}_Cmd", default_value=False)
        builder.add_numeric_writable(f"{name}_Runtime_Seconds", default_value=0.0)

    # --- Intermediate Logic Outputs for Visibility ---
    builder.add_numeric_writable("Total_Chillers_Running", default_value=0.0)

    print("\n--- Creating Logic Components inside 'Logic' sub-folder ---")
    builder.start_sub_folder("Logic")

    # --- Staging Blocks ---
    builder.add_lead_lag_runtime(
        "Chiller_LeadLag", properties={"numberOutputs": 3, "maxRuntime": "200h"}
    )
    builder.add_lead_lag_runtime(
        "Pump_LeadLag", properties={"numberOutputs": 3, "maxRuntime": "200h"}
    )

    # --- Command Gating Logic (NEW CLEANER PATTERN) ---
    for name in all_equipment_names:
        builder.add_and(f"{name}_Cmd_Gate")

    # --- Runtime Accumulation & Latching ---
    builder.add_multi_vibrator("One_Second_Timer", period_ms="1000")
    builder.add_one_shot("Timer_Pulse")
    builder.add_numeric_const("Increment_Value", value=1.0)
    for name in all_equipment_names:
        builder.add_counter(f"{name}_RuntimeCounter")
        builder.add_and(f"{name}_IncrementGate")
        builder.add_numeric_latch(f"{name}_RuntimeLatch")
        builder.add_not(f"{name}_Cmd_Off_Detector")

    # --- Interlock to calculate Pump Demand & Convert Demands to Boolean ---
    builder.add_numeric_const("Const_1", value=1.0)
    builder.add_numeric_const("Const_0", value=0.0)
    builder.add_greater_than("Is_Chiller_Demand_Active")
    builder.add_greater_than("Is_Pump_Demand_Active")
    for name in chiller_names:
        builder.add_numeric_switch(f"{name}_BoolToNum")
    builder.add_add("Sum_Running_Chillers")

    builder.end_sub_folder()

    print("\n--- Wiring Components ---")

    # --- Wire Master Timer ---
    builder.add_link("One_Second_Timer", "out", "Timer_Pulse", "in")

    # --- CORRECTED: Convert Numeric Demands to Boolean Enables for LeadLag Blocks ---
    # Per user feedback, the '.in' slot must be driven by a boolean output.
    # This logic converts any numeric demand > 0 into a boolean 'true'.
    builder.add_link("Chiller_Demand_Raw", "out", "Is_Chiller_Demand_Active", "inA")
    builder.add_link("Const_0", "out", "Is_Chiller_Demand_Active", "inB")
    builder.add_link("Is_Chiller_Demand_Active", "out", "Chiller_LeadLag", "in")

    builder.add_link("Sum_Running_Chillers", "out", "Is_Pump_Demand_Active", "inA")
    builder.add_link("Const_0", "out", "Is_Pump_Demand_Active", "inB")
    builder.add_link("Is_Pump_Demand_Active", "out", "Pump_LeadLag", "in")

    # --- Wire Commands through Final Enable Gates ---
    equip_map = {"A": chiller_names[0], "B": chiller_names[1], "C": chiller_names[2]}
    pump_map = {"A": pump_names[0], "B": pump_names[1], "C": pump_names[2]}

    for slot, name in equip_map.items():  # Chillers
        builder.add_link("Chiller_LeadLag", f"out{slot}", f"{name}_Cmd_Gate", "inA")
        builder.add_link("Plant_Enable", "out", f"{name}_Cmd_Gate", "inB")
        builder.add_link(f"{name}_Cmd_Gate", "out", f"{name}_Cmd", "in16")

    for slot, name in pump_map.items():  # Pumps
        builder.add_link("Pump_LeadLag", f"out{slot}", f"{name}_Cmd_Gate", "inA")
        builder.add_link("Plant_Enable", "out", f"{name}_Cmd_Gate", "inB")
        builder.add_link(f"{name}_Cmd_Gate", "out", f"{name}_Cmd", "in16")

    # --- Wire Runtime, and Latching Logic ---
    for name in all_equipment_names:
        lead_lag_block = "Chiller_LeadLag" if "Chiller" in name else "Pump_LeadLag"

        # Determine the correct runtime slot (runtimeA, runtimeB, etc.)
        runtime_slot = ""
        if "Chiller_1" in name or "Pump_1" in name:
            runtime_slot = "runtimeA"
        elif "Chiller_2" in name or "Pump_2" in name:
            runtime_slot = "runtimeB"
        elif "Chiller_3" in name or "Pump_3" in name:
            runtime_slot = "runtimeC"

        # Wire runtime accumulation
        builder.add_link("Timer_Pulse", "out", f"{name}_IncrementGate", "inA")
        builder.add_link(
            f"{name}_Cmd", "out", f"{name}_IncrementGate", "inB"
        )  # Use final gated command
        builder.add_link(
            f"{name}_IncrementGate", "out", f"{name}_RuntimeCounter", "countUp"
        )
        builder.add_link(
            "Increment_Value", "out", f"{name}_RuntimeCounter", "countIncrement"
        )

        # Wire runtime display and latching
        builder.add_link(
            f"{name}_RuntimeCounter", "out", f"{name}_Runtime_Seconds", "in16"
        )
        builder.add_link(f"{name}_RuntimeCounter", "out", f"{name}_RuntimeLatch", "in")
        builder.add_link(
            f"{name}_Cmd", "out", f"{name}_Cmd_Off_Detector", "in"
        )  # Use final gated command
        builder.add_link(
            f"{name}_Cmd_Off_Detector", "out", f"{name}_RuntimeLatch", "clock"
        )

        # Wire latched runtime back to the correct lead-lag block
        if runtime_slot:
            builder.add_link(
                f"{name}_RuntimeLatch",
                "out",
                lead_lag_block,
                runtime_slot,
                link_type="b:ConversionLink",
                converter_type="conv:StatusNumericToRelTime",
            )

    # --- Wire Interlock Logic ---
    for i, name in enumerate(chiller_names):
        slot = chr(ord("A") + i)
        builder.add_link(
            f"{name}_Cmd", "out", f"{name}_BoolToNum", "inSwitch"
        )  # Use final gated command
        builder.add_link("Const_1", "out", f"{name}_BoolToNum", "inTrue")
        builder.add_link(
            f"{name}_BoolToNum", "out", "Sum_Running_Chillers", f"in{slot}"
        )

    builder.add_link("Sum_Running_Chillers", "out", "Total_Chillers_Running", "in16")

    # --- Save the .bog file ---
    bog_filename = "hvac_simple_chiller_plant_three.bog"
    output_path = os.path.join(args.output_dir, bog_filename)
    os.makedirs(args.output_dir, exist_ok=True)
    builder.save(output_path)

    print(
        f"\nSuccessfully created Niagara .bog file at: {os.path.abspath(output_path)}"
    )


if __name__ == "__main__":
    main()
