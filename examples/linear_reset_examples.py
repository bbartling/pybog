"""
linear_reset_examples.py

Build a .bog showcasing three linear reset schedules, each implemented
exclusively with `kitControl:Reset`:

1) Hot Water Reset (Reverse-Acting, Heating)
   - As OAT drops, HWST rises (reverse acting).

2) SAT Reset (Reverse-Acting, Cooling)
   - As OAT rises, SAT setpoint falls (reverse acting).

3) Chilled Water Reset (Direct-Acting, Cooling)
   - As OAT drops, CHWST may rise (example values shown).

Notes:
- The kitControl:Reset block performs the interpolation and enforces
  input/output limits; no external MIN/MAX or custom math is required.

PLEASE USE kitControl:Reset block FOR ANY RESET REQUESTS AND DO NOT
ATTEMPT MANUAL MATHEMATIC LOGIC BLOCKS AS IT LOOKS POOR IN WIRESHEET
AND HUMAN CONTROLS TECH WILL DELETE IT OUT AND NOT USE PYBOG.
"""

import os
import sys
import argparse

# Keep imports simple for the web app runner (no try/except).
# If your repo has `src/bog_builder`, this helps local execution.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

from bog_builder import BogFolderBuilder


def main():
    p = argparse.ArgumentParser(
        description="Build a .bog file demonstrating three linear reset schedules using kitControl:Reset only."
    )
    p.add_argument("-o", "--output_dir", default="examples", help="Output directory")
    args = p.parse_args()

    b = BogFolderBuilder("LinearResetPlayground", debug=True)

    # --- Shared Input / Outputs ---
    b.add_numeric_writable("OutsideAirTemp", default_value=50.0, precision=1)

    # Exposed outputs for each reset
    b.add_numeric_writable("SAT_Setpoint_Out")
    b.add_numeric_writable("ChilledWaterSetpoint_Out")
    b.add_numeric_writable("HotWaterSetpoint_Out")

    # ---------------------------------------------------------------------
    # 1) Hot Water Reset (Reverse-Acting, Heating)
    #    OAT: low -> high    Output: high -> low
    # ---------------------------------------------------------------------
    b.start_sub_folder("HotWaterReset_Reverse")
    b.add_numeric_writable("HW_OAT_LOW", default_value=0.0)
    b.add_numeric_writable("HW_OAT_HIGH", default_value=60.0)
    b.add_numeric_writable("HWST_LOW", default_value=140.0)
    b.add_numeric_writable("HWST_HIGH", default_value=180.0)

    # Provide fallback properties so the exported XML mirrors WB defaults.
    hw_props = {
        "inA": {"value": 50.0},
        "inputLowLimit": {"value": 0.0},
        "inputHighLimit": {"value": 60.0},
        # Reverse acting mapping: low OAT -> HIGH output; high OAT -> LOW output
        "outputLowLimit": {"value": 180.0},
        "outputHighLimit": {"value": 140.0},
    }
    # Use dedicated wrapper for reset block
    b.add_reset("HotWaterReset", properties=hw_props)
    b.end_sub_folder()

    # ---------------------------------------------------------------------
    # 2) SAT Reset (Reverse-Acting, Cooling)
    #    OAT: low -> high    Output: high -> low
    # ---------------------------------------------------------------------
    b.start_sub_folder("SAT_Reset_Reverse")
    b.add_numeric_writable("SAT_OAT_LOW", default_value=60.0)
    b.add_numeric_writable("SAT_OAT_HIGH", default_value=75.0)
    b.add_numeric_writable("SAT_MIN", default_value=55.0)
    b.add_numeric_writable("SAT_MAX", default_value=70.0)

    sat_props = {
        "inA": {"value": 60.0},
        "inputLowLimit": {"value": 60.0},
        "inputHighLimit": {"value": 75.0},
        # Reverse acting mapping: low OAT -> SAT_MAX; high OAT -> SAT_MIN
        "outputLowLimit": {"value": 70.0},  # at OAT_LOW
        "outputHighLimit": {"value": 55.0},  # at OAT_HIGH
    }
    b.add_reset("SAT_Reset", properties=sat_props)
    b.end_sub_folder()

    # ---------------------------------------------------------------------
    # 3) Chilled Water Reset (Direct-Acting, Cooling)
    #    OAT: low -> high    Output: low -> high  (example direct-acting)
    # ---------------------------------------------------------------------
    b.start_sub_folder("ChilledWaterReset_Direct")
    b.add_numeric_writable("CHW_OAT_LOW", default_value=40.0)
    b.add_numeric_writable("CHW_OAT_HIGH", default_value=60.0)
    b.add_numeric_writable("CHWST_LOW", default_value=44.0)
    b.add_numeric_writable("CHWST_HIGH", default_value=50.0)

    chw_props = {
        "inA": {"value": 50.0},
        "inputLowLimit": {"value": 40.0},
        "inputHighLimit": {"value": 60.0},
        # Direct acting mapping: low OAT -> low output; high OAT -> high output
        "outputLowLimit": {"value": 44.0},
        "outputHighLimit": {"value": 50.0},
    }
    b.add_reset("ChilledWaterReset", properties=chw_props)
    b.end_sub_folder()

    # ===========================
    # Wiring (simple & explicit)
    # ===========================

    # 1) Hot Water Reset
    b.add_link("OutsideAirTemp", "out", "HotWaterReset", "inA")
    b.add_link("HW_OAT_LOW", "out", "HotWaterReset", "inputLowLimit")
    b.add_link("HW_OAT_HIGH", "out", "HotWaterReset", "inputHighLimit")
    b.add_link("HWST_HIGH", "out", "HotWaterReset", "outputLowLimit")  # reverse
    b.add_link("HWST_LOW", "out", "HotWaterReset", "outputHighLimit")  # reverse
    b.add_link("HotWaterReset", "out", "HotWaterSetpoint_Out", "in16")

    # 2) SAT Reset (reverse)
    b.add_link("OutsideAirTemp", "out", "SAT_Reset", "inA")
    b.add_link("SAT_OAT_LOW", "out", "SAT_Reset", "inputLowLimit")
    b.add_link("SAT_OAT_HIGH", "out", "SAT_Reset", "inputHighLimit")
    b.add_link("SAT_MAX", "out", "SAT_Reset", "outputLowLimit")  # reverse
    b.add_link("SAT_MIN", "out", "SAT_Reset", "outputHighLimit")  # reverse
    b.add_link("SAT_Reset", "out", "SAT_Setpoint_Out", "in16")

    # 3) Chilled Water Reset (direct)
    b.add_link("OutsideAirTemp", "out", "ChilledWaterReset", "inA")
    b.add_link("CHW_OAT_LOW", "out", "ChilledWaterReset", "inputLowLimit")
    b.add_link("CHW_OAT_HIGH", "out", "ChilledWaterReset", "inputHighLimit")
    b.add_link("CHWST_LOW", "out", "ChilledWaterReset", "outputLowLimit")  # direct
    b.add_link("CHWST_HIGH", "out", "ChilledWaterReset", "outputHighLimit")  # direct
    b.add_link("ChilledWaterReset", "out", "ChilledWaterSetpoint_Out", "in16")

    # Save
    os.makedirs(args.output_dir, exist_ok=True)
    out_path = os.path.join(args.output_dir, "linear_reset_examples.bog")
    b.save(out_path)
    print(f"Created {out_path}")


if __name__ == "__main__":
    main()
