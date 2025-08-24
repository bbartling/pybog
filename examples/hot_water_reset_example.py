"""
A classic HVAC algorithm for a hot water reset schedule. This script uses a
`kitControl:Reset` block to calculate a hot water supply temperature setpoint
based on the outside air temperature (OAT). As the OAT gets colder, the hot
water setpoint gets hotter, and vice-versa. This is a common energy-saving
strategy for boiler systems.
"""

from __future__ import annotations

import argparse
import os
import sys

from bog_builder import BogFolderBuilder


def build_hot_water_reset(output_directory: str) -> str:
    """Build the hot water reset .bog file.

    Parameters
    ----------
    output_directory : str
        Destination directory in which to write the .bog file.  The
        directory will be created if it does not exist.

    Returns
    -------
    str
        The full path to the generated .bog file.
    """
    # Create builder with a descriptive folder name
    builder = BogFolderBuilder("HotWaterTempReset", debug=False)

    # Define numeric writables for outdoor air temperature and limits
    builder.add_numeric_writable("OAT", default_value=11.0)
    builder.add_numeric_writable("OAT_LOW", default_value=0.0)
    builder.add_numeric_writable("OAT_HIGH", default_value=50.0)
    builder.add_numeric_writable("HWST_LOW", default_value=110.0)
    builder.add_numeric_writable("HWST_HIGH", default_value=160.0)

    # The Reset block takes five inputs and produces a single out output.
    # Provide fallback values matching the initial values of the connected
    # writables so the exported XML mirrors Workbench behaviour.  The
    # properties dict expects a nested dict with a ``value`` key.
    reset_properties = {
        "inA": {"value": 11.0},
        "inputLowLimit": {"value": 0.0},
        "inputHighLimit": {"value": 50.0},
        "outputLowLimit": {"value": 160.0},
        "outputHighLimit": {"value": 110.0},
    }
    builder.add_component("kitControl:Reset", "Reset", properties=reset_properties)

    # Output writable for the supply temperature setpoint
    builder.add_numeric_writable("HotWaterSupplyTempStp")

    # Create the links between components.  Note that each target slot
    # corresponds to a named slot on the Reset block or the numeric writable.
    builder.add_link("OAT", "out", "Reset", "inA")
    builder.add_link("OAT_LOW", "out", "Reset", "inputLowLimit")
    builder.add_link("OAT_HIGH", "out", "Reset", "inputHighLimit")
    builder.add_link("HWST_HIGH", "out", "Reset", "outputLowLimit")
    builder.add_link("HWST_LOW", "out", "Reset", "outputHighLimit")
    builder.add_link("Reset", "out", "HotWaterSupplyTempStp", "in10")

    # Write the .bog file
    os.makedirs(output_directory, exist_ok=True)
    output_path = os.path.join(output_directory, "HotWaterTempReset.bog")
    builder.save(output_path)
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a hot water reset .bog file."
    )
    parser.add_argument(
        "-o",
        "--output",
        default="examples",
        help=(
            "Directory to write the output .bog file.  If omitted, the file is "
            "written to an 'examples' folder next to this script."
        ),
    )
    args = parser.parse_args()
    out_dir = args.output
    full_path = build_hot_water_reset(out_dir)
    print(f"Created {full_path}")


if __name__ == "__main__":
    main()
