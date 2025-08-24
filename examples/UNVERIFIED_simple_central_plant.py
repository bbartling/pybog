"""
simple_central_plant.py

Builds a Niagara .bog that implements a central plant mode selector with:
- heating/cooling start/stop based on OAT with hysteresis
- a free-cooling (economizer) deadband
- boolean outputs for boiler/chiller and pumps

This script conforms to the project conventions:
- appends ../src to sys.path (no try/except)
- accepts an output directory via -o/--output_dir
- saves to a hard-coded .bog filename inside that directory
"""

from __future__ import annotations

import argparse
import os
import sys

# Project import convention: append ../src then import the builder
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))
from bog_builder import BogFolderBuilder  # noqa: E402


SCRIPT_FOLDER_NAME = "CentralPlantControl"
SCRIPT_BOG_NAME = "simple_central_plant.bog"


def build_central_plant(builder: BogFolderBuilder) -> None:
    """
    Populate a BogFolderBuilder with central plant logic:
      - Hysteretic heat/cool start/stop vs OAT
      - Free-cooling zone blocks heating/cooling
    """
    # --- Inputs / Setpoints (top-level “variables”) ---
    builder.add_numeric_writable("OAT", default_value=55.0)

    # Heating (start below stop to create hysteresis)
    builder.add_numeric_writable("HeatStartSP", default_value=45.0)
    builder.add_numeric_writable("HeatStopSP", default_value=50.0)

    # Cooling (start above stop to create hysteresis)
    builder.add_numeric_writable("CoolStartSP", default_value=75.0)
    builder.add_numeric_writable("CoolStopSP", default_value=70.0)

    # Free cooling deadband (inclusive range)
    builder.add_numeric_writable("FreeCoolLow", default_value=50.0)
    builder.add_numeric_writable("FreeCoolHigh", default_value=60.0)

    # --- Outputs to equipment ---
    builder.add_boolean_writable("Boiler_Cmd")
    builder.add_boolean_writable("HeatingPump_Cmd")
    builder.add_boolean_writable("Chiller_Cmd")
    builder.add_boolean_writable("CoolingPump_Cmd")

    # --- Logic subfolder (keeps top level clean) ---
    builder.start_sub_folder("PlantLogic")

    # Free-cooling band: OAT >= Low AND OAT <= High
    builder.add_component("kitControl:GreaterThanEqual", "FreeCool_GE")
    builder.add_component("kitControl:LessThanEqual", "FreeCool_LE")
    builder.add_component("kitControl:And", "FreeCoolingMode")
    builder.add_component("kitControl:Not", "Not_FreeCooling")

    # Start/Stop comparators
    builder.add_component(
        "kitControl:LessThanEqual", "HeatStart_Compare"
    )  # OAT <= HeatStartSP
    builder.add_component(
        "kitControl:GreaterThanEqual", "HeatStop_Compare"
    )  # OAT >= HeatStopSP
    builder.add_component(
        "kitControl:GreaterThanEqual", "CoolStart_Compare"
    )  # OAT >= CoolStartSP
    builder.add_component(
        "kitControl:LessThanEqual", "CoolStop_Compare"
    )  # OAT <= CoolStopSP

    # Start/Stop gates
    builder.add_component(
        "kitControl:And", "HeatStart_Gate"
    )  # start & not free-cooling
    builder.add_component("kitControl:And", "CoolStart_Gate")
    builder.add_component("kitControl:Or", "HeatStop_Or")  # stop OR free-cooling
    builder.add_component("kitControl:Or", "CoolStop_Or")

    # Latches (hysteresis behavior)
    builder.add_component("kitControl:BooleanLatch", "Heat_Latch")
    builder.add_component("kitControl:BooleanLatch", "Cool_Latch")

    # --- Wiring: Free cooling detection ---
    builder.add_link("OAT", "out", "FreeCool_GE", "inA")
    builder.add_link("FreeCoolLow", "out", "FreeCool_GE", "inB")

    builder.add_link("OAT", "out", "FreeCool_LE", "inA")
    builder.add_link("FreeCoolHigh", "out", "FreeCool_LE", "inB")

    builder.add_link("FreeCool_GE", "out", "FreeCoolingMode", "inA")
    builder.add_link("FreeCool_LE", "out", "FreeCoolingMode", "inB")

    builder.add_link("FreeCoolingMode", "out", "Not_FreeCooling", "in")

    # --- Wiring: Heating start/stop with gating ---
    builder.add_link("OAT", "out", "HeatStart_Compare", "inA")
    builder.add_link("HeatStartSP", "out", "HeatStart_Compare", "inB")
    builder.add_link("HeatStart_Compare", "out", "HeatStart_Gate", "inA")
    builder.add_link("Not_FreeCooling", "out", "HeatStart_Gate", "inB")

    builder.add_link("OAT", "out", "HeatStop_Compare", "inA")
    builder.add_link("HeatStopSP", "out", "HeatStop_Compare", "inB")
    builder.add_link("HeatStop_Compare", "out", "HeatStop_Or", "inA")
    builder.add_link("FreeCoolingMode", "out", "HeatStop_Or", "inB")

    # --- Wiring: Cooling start/stop with gating ---
    builder.add_link("OAT", "out", "CoolStart_Compare", "inA")
    builder.add_link("CoolStartSP", "out", "CoolStart_Compare", "inB")
    builder.add_link("CoolStart_Compare", "out", "CoolStart_Gate", "inA")
    builder.add_link("Not_FreeCooling", "out", "CoolStart_Gate", "inB")

    builder.add_link("OAT", "out", "CoolStop_Compare", "inA")
    builder.add_link("CoolStopSP", "out", "CoolStop_Compare", "inB")
    builder.add_link("CoolStop_Compare", "out", "CoolStop_Or", "inA")
    builder.add_link("FreeCoolingMode", "out", "CoolStop_Or", "inB")

    # --- Wiring: Latches (Set/Reset) ---
    builder.add_link("HeatStart_Gate", "out", "Heat_Latch", "set")
    builder.add_link("HeatStop_Or", "out", "Heat_Latch", "reset")

    builder.add_link("CoolStart_Gate", "out", "Cool_Latch", "set")
    builder.add_link("CoolStop_Or", "out", "Cool_Latch", "reset")

    builder.end_sub_folder()

    # --- Final outputs (latch → writable) ---
    builder.add_link("Heat_Latch", "out", "Boiler_Cmd", "in16")
    builder.add_link("Heat_Latch", "out", "HeatingPump_Cmd", "in16")
    builder.add_link("Cool_Latch", "out", "Chiller_Cmd", "in16")
    builder.add_link("Cool_Latch", "out", "CoolingPump_Cmd", "in16")


def main() -> None:
    p = argparse.ArgumentParser(
        description="Generate a central plant .bog with hysteresis and free-cooling."
    )
    p.add_argument(
        "-o",
        "--output_dir",
        default="examples",
        help="Directory to write the .bog file.",
    )
    args = p.parse_args()

    # Build graph
    builder = BogFolderBuilder(SCRIPT_FOLDER_NAME, debug=False)
    build_central_plant(builder)

    # Save to hard-coded name inside the chosen output directory
    os.makedirs(args.output_dir, exist_ok=True)
    out_path = os.path.join(args.output_dir, SCRIPT_BOG_NAME)
    builder.save(out_path)
    print(f"Successfully created Niagara .bog file at: {os.path.abspath(out_path)}")


if __name__ == "__main__":
    main()
