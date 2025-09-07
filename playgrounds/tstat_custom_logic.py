"""
thermostat.py

This is custom logic with bool comparaters. In General do not use
this as humans controls techs prefer to visually see the Tstat
block being used from kitControl because it is what they are
used to seeing and they may reject logic that looks like
this.

Simple thermostat logic:
- Modes: 0=Off, 1=Heat, 2=Cool  (numeric select)
- Hysteresis applied on both heat/cool thresholds
- Fan runs when heating or cooling, or when FanAuto is false (manual/override)

Conventions:
- Appends ../src to sys.path (no try/except)
- Accepts -o/--output_dir
- Saves to a hard-coded 'thermostat.bog' in that directory
"""

from __future__ import annotations

import argparse
import os
import sys

# Project import convention: append ../src then import the builder
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))
from bog_builder import BogFolderBuilder  # noqa: E402

SCRIPT_FOLDER_NAME = "Thermostat"
SCRIPT_BOG_NAME = "thermostat.bog"


def build_thermostat(builder: BogFolderBuilder) -> None:
    """
    Build thermostat logic using kitControl blocks.
    """
    # -------- Top-level “variables” --------
    builder.add_numeric_writable("SpaceTemp", default_value=72.0)
    builder.add_numeric_writable("HeatSP", default_value=68.0)
    builder.add_numeric_writable("CoolSP", default_value=74.0)
    builder.add_numeric_writable("Hysteresis", default_value=1.0)
    # Mode: 0=Off, 1=Heat, 2=Cool
    builder.add_numeric_writable("Mode", default_value=0.0)
    # FanAuto = True means fan follows calls; False forces continuous fan
    builder.add_boolean_writable("FanAuto", default_value=True)

    # Outputs
    builder.add_boolean_writable("Output_HeatCmd")
    builder.add_boolean_writable("Output_CoolCmd")
    builder.add_boolean_writable("Output_FanCmd")

    # -------- Logic (sub-folder) --------
    builder.start_sub_folder("ThermostatLogic")

    # Constants (1 and 2) for Mode comparisons
    builder.add_numeric_const("Const1", properties={"value": 1})
    builder.add_numeric_const("Const2", properties={"value": 2})

    # Mode == 1 (Heat): Mode ≥ 1 AND Mode ≤ 1
    builder.add_greater_than_equal("Mode_GE_1")
    builder.add_less_than_equal("Mode_LE_1")
    builder.add_and("IsHeatMode")

    # Mode == 2 (Cool): Mode ≥ 2 AND Mode ≤ 2
    builder.add_greater_than_equal("Mode_GE_2")
    builder.add_less_than_equal("Mode_LE_2")
    builder.add_and("IsCoolMode")

    # Sum blocks for hysteresis
    builder.add_add("SpacePlusHyst")
    builder.add_add("CoolSP_plus_Hyst")

    # Threshold compares
    builder.add_less_than_equal("IsBelowHeat")  # Space+Hyst <= HeatSP
    builder.add_greater_than_equal("IsAboveCool")  # Space >= CoolSP+Hyst

    # Command gates
    builder.add_and("HeatCmdGate")  # IsHeatMode AND IsBelowHeat
    builder.add_and("CoolCmdGate")  # IsCoolMode AND IsAboveCool

    # Fan logic: (HeatCmd OR CoolCmd) OR (NOT FanAuto)
    builder.add_or("HeatOrCool")
    builder.add_not("FanAutoNot")
    builder.add_or("FanCmdGate")

    # ---- Wiring: Mode == 1 (Heat) ----
    builder.add_link("Mode", "out", "Mode_GE_1", "inA")
    builder.add_link("Const1", "out", "Mode_GE_1", "inB")
    builder.add_link("Mode", "out", "Mode_LE_1", "inA")
    builder.add_link("Const1", "out", "Mode_LE_1", "inB")
    builder.add_link("Mode_GE_1", "out", "IsHeatMode", "inA")
    builder.add_link("Mode_LE_1", "out", "IsHeatMode", "inB")

    # ---- Wiring: Mode == 2 (Cool) ----
    builder.add_link("Mode", "out", "Mode_GE_2", "inA")
    builder.add_link("Const2", "out", "Mode_GE_2", "inB")
    builder.add_link("Mode", "out", "Mode_LE_2", "inA")
    builder.add_link("Const2", "out", "Mode_LE_2", "inB")
    builder.add_link("Mode_GE_2", "out", "IsCoolMode", "inA")
    builder.add_link("Mode_LE_2", "out", "IsCoolMode", "inB")

    # ---- Wiring: Hysteresis adds ----
    builder.add_link("SpaceTemp", "out", "SpacePlusHyst", "inA")
    builder.add_link("Hysteresis", "out", "SpacePlusHyst", "inB")
    builder.add_link("CoolSP", "out", "CoolSP_plus_Hyst", "inA")
    builder.add_link("Hysteresis", "out", "CoolSP_plus_Hyst", "inB")

    # ---- Thresholds ----
    builder.add_link("SpacePlusHyst", "out", "IsBelowHeat", "inA")
    builder.add_link("HeatSP", "out", "IsBelowHeat", "inB")

    builder.add_link("SpaceTemp", "out", "IsAboveCool", "inA")
    builder.add_link("CoolSP_plus_Hyst", "out", "IsAboveCool", "inB")

    # ---- Command gates ----
    builder.add_link("IsHeatMode", "out", "HeatCmdGate", "inA")
    builder.add_link("IsBelowHeat", "out", "HeatCmdGate", "inB")

    builder.add_link("IsCoolMode", "out", "CoolCmdGate", "inA")
    builder.add_link("IsAboveCool", "out", "CoolCmdGate", "inB")

    # ---- Fan logic ----
    builder.add_link("HeatCmdGate", "out", "HeatOrCool", "inA")
    builder.add_link("CoolCmdGate", "out", "HeatOrCool", "inB")

    builder.add_link("FanAuto", "out", "FanAutoNot", "in")
    builder.add_link("HeatOrCool", "out", "FanCmdGate", "inA")
    builder.add_link("FanAutoNot", "out", "FanCmdGate", "inB")

    builder.end_sub_folder()

    # Final outputs
    builder.add_link("HeatCmdGate", "out", "Output_HeatCmd", "in16")
    builder.add_link("CoolCmdGate", "out", "Output_CoolCmd", "in16")
    builder.add_link("FanCmdGate", "out", "Output_FanCmd", "in16")


def main() -> None:
    p = argparse.ArgumentParser(description="Generate a thermostat .bog file.")
    p.add_argument(
        "-o",
        "--output_dir",
        default="examples",
        help="Directory to write the .bog file.",
    )
    args = p.parse_args()

    builder = BogFolderBuilder(SCRIPT_FOLDER_NAME, debug=True)
    build_thermostat(builder)

    os.makedirs(args.output_dir, exist_ok=True)
    out_path = os.path.join(args.output_dir, SCRIPT_BOG_NAME)
    builder.save(out_path)
    print(f"Successfully created Niagara .bog file at: {os.path.abspath(out_path)}")


if __name__ == "__main__":
    main()
