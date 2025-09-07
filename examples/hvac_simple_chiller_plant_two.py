"""
Human asks via Chat input:

Create a Niagara .bog file for a plant with three chillers and three primary pumps.
Each chiller shall be staged for lead, lag, and standby based on runtime.
Each primary pump shall be staged for lead, lag, and standby based on runtime.
Calculate the total number of running chillers. Use this count as the demand signal
for the pumps (e.g., if 2 chillers are running, then run a minimum of 2 pumps).
Track runtime for all 6 pieces of equipment and expose the runtime in seconds as top-level outputs.
"""

import os
import argparse
from bog_builder import BogFolderBuilder


def main():

    # --- Setup argument parser ---
    parser = argparse.ArgumentParser(
        description="Build a chiller plant staging logic with runtime-based rotation."
    )
    parser.add_argument(
        "-o", "--output_dir", default="examples", help="Output directory for the .bog file."
    )
    args = parser.parse_args()

    # Initialize the BogFolderBuilder with the top-level folder name.
    builder = BogFolderBuilder("Chiller_Pump_Staging", debug=True)

    # --- Configuration Constants ---
    NUM_EQUIPMENT = 3
    CHILLER_MAX_RUNTIME = "200h"
    PUMP_MAX_RUNTIME = "200h"
    TIMER_PERIOD_MS = "1000"  # 1 second pulse for runtime accumulation

    # --- Top-Level Inputs & Outputs ---
    print("--- Creating Top-Level Inputs & Outputs ---")

    # System Master Input: Number of chillers requested to run (0-3)
    builder.add_numeric_writable("Chiller_Demand", default_value=0.0)

    # Equipment Command & Runtime Outputs
    chiller_names = [f"Chiller_{i+1}" for i in range(NUM_EQUIPMENT)]
    pump_names = [f"Pump_{i+1}" for i in range(NUM_EQUIPMENT)]

    for name in chiller_names:
        builder.add_boolean_writable(f"{name}_Cmd", default_value=False)
        builder.add_numeric_writable(f"{name}_Runtime_Seconds", default_value=0.0)

    for name in pump_names:
        builder.add_boolean_writable(f"{name}_Cmd", default_value=False)
        builder.add_numeric_writable(f"{name}_Runtime_Seconds", default_value=0.0)

    # Intermediate Logic Outputs for Visibility
    builder.add_numeric_writable("Total_Chillers_Running", default_value=0.0)
    builder.add_numeric_writable("Pump_Demand", default_value=0.0)

    # --- Logic Components (organized inside a single sub-folder) ---
    print("\n--- Creating Logic Components inside 'Logic' sub-folder ---")
    builder.start_sub_folder("Logic")

    # --- Staging Blocks ---
    builder.add_lead_lag_runtime(
        "Chiller_LeadLag",
        properties={"numberOutputs": NUM_EQUIPMENT, "maxRuntime": CHILLER_MAX_RUNTIME},
    )
    builder.add_lead_lag_runtime(
        "Pump_LeadLag",
        properties={"numberOutputs": NUM_EQUIPMENT, "maxRuntime": PUMP_MAX_RUNTIME},
    )

    # --- Runtime Accumulation Timer ---
    builder.add_multi_vibrator("One_Second_Timer", period_ms=TIMER_PERIOD_MS)
    builder.add_one_shot("Timer_Pulse")
    builder.add_numeric_const("Increment_Value", value=1.0)

    # --- Runtime Logic for each piece of equipment ---
    for name in chiller_names + pump_names:
        builder.add_counter(f"{name}_RuntimeCounter")
        builder.add_and(f"{name}_IncrementGate")

    # --- Interlock: Count Running Chillers to determine Pump Demand ---
    builder.add_numeric_const("Const_1", value=1.0)
    for name in chiller_names:
        builder.add_numeric_switch(f"{name}_BoolToNum")

    builder.add_add("Sum_Running_Chillers")

    builder.end_sub_folder()

    # --- Wiring ---
    print("\n--- Wiring Components ---")

    # --- 1. Wire Master Timer ---
    # MultiVibrator output triggers OneShot to create a clean pulse every second.
    builder.add_link("One_Second_Timer", "out", "Timer_Pulse", "in")

    # --- 2. Wire Chiller Staging ---
    # External demand signal drives the chiller lead/lag block.
    builder.add_link("Chiller_Demand", "out", "Chiller_LeadLag", "in")

    # --- 3. Wire Runtime and Commands for Chillers and Pumps ---
    equip_map = {
        "A": (chiller_names[0], pump_names[0]),
        "B": (chiller_names[1], pump_names[1]),
        "C": (chiller_names[2], pump_names[2]),
    }

    for slot, (chiller_name, pump_name) in equip_map.items():
        # --- Chiller Command and Runtime Calculation ---
        # LeadLag output -> Chiller Command output point
        builder.add_link(f"Chiller_LeadLag", f"out{slot}", f"{chiller_name}_Cmd", "in16")
        # Runtime Gate: Timer_Pulse AND Chiller_Cmd must both be true to increment counter.
        builder.add_link("Timer_Pulse", "out", f"{chiller_name}_IncrementGate", "inA")
        builder.add_link(f"{chiller_name}_Cmd", "out", f"{chiller_name}_IncrementGate", "inB")
        builder.add_link(
            f"{chiller_name}_IncrementGate", "out", f"{chiller_name}_RuntimeCounter", "countUp"
        )
        # Set counter increment value to 1.
        builder.add_link(
            "Increment_Value", "out", f"{chiller_name}_RuntimeCounter", "countIncrement"
        )
        # Counter output -> Runtime_Seconds output point
        builder.add_link(
            f"{chiller_name}_RuntimeCounter", "out", f"{chiller_name}_Runtime_Seconds", "in16"
        )
        # Feedback loop: Counter output -> LeadLag runtime input (converts seconds to runtime format)
        builder.add_link(
            f"{chiller_name}_RuntimeCounter", "out", "Chiller_LeadLag", f"runtime{slot}"
        )

        # --- Pump Command and Runtime Calculation (identical logic) ---
        builder.add_link(f"Pump_LeadLag", f"out{slot}", f"{pump_name}_Cmd", "in16")
        builder.add_link("Timer_Pulse", "out", f"{pump_name}_IncrementGate", "inA")
        builder.add_link(f"{pump_name}_Cmd", "out", f"{pump_name}_IncrementGate", "inB")
        builder.add_link(
            f"{pump_name}_IncrementGate", "out", f"{pump_name}_RuntimeCounter", "countUp"
        )
        builder.add_link(
            "Increment_Value", "out", f"{pump_name}_RuntimeCounter", "countIncrement"
        )
        builder.add_link(
            f"{pump_name}_RuntimeCounter", "out", f"{pump_name}_Runtime_Seconds", "in16"
        )
        builder.add_link(
            f"{pump_name}_RuntimeCounter", "out", "Pump_LeadLag", f"runtime{slot}"
        )

    # --- 4. Wire Interlock Logic ---
    # Convert each chiller command boolean to a number (1 if true, 0 if false)
    for i, name in enumerate(chiller_names):
        slot_letter = chr(ord('A') + i)
        builder.add_link(f"{name}_Cmd", "out", f"{name}_BoolToNum", "inSwitch")
        builder.add_link("Const_1", "out", f"{name}_BoolToNum", "inTrue")
        # inFalse defaults to 0.0, so no explicit link needed.
        builder.add_link(f"{name}_BoolToNum", "out", "Sum_Running_Chillers", f"in{slot_letter}")

    # The sum of running chillers drives the pump demand.
    builder.add_link("Sum_Running_Chillers", "out", "Total_Chillers_Running", "in16")
    builder.add_link("Sum_Running_Chillers", "out", "Pump_Demand", "in16")
    builder.add_link("Sum_Running_Chillers", "out", "Pump_LeadLag", "in")

    # --- Save the .bog file ---
    os.makedirs(args.output_dir, exist_ok=True)
    bog_filename = "chiller_pump_staging.bog"
    output_path = os.path.join(args.output_dir, bog_filename)
    builder.save(output_path)

    print(f"\nSuccessfully created Niagara .bog file at: {os.path.abspath(output_path)}")


if __name__ == "__main__":
    main()