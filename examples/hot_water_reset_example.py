"""Example script for generating a hot water reset .bog file.

This script demonstrates how to construct a linear hot water supply
temperature reset using the :class:`BogFolderBuilder` from the
``bog_builder`` package.  The reset linearly maps the outdoor air
temperature (OAT) between low/high limits to a corresponding supply
temperature setpoint between low and high limits.  The resulting
.bog file can be imported directly into Niagara Workbench.

Usage
-----

Run the script from the command line.  By default, the output is
written into a folder named ``examples`` relative to the script
location.  To specify a different directory, use the ``-o`` flag:

```
python hot_water_reset_example.py -o "C:\\Users\\ben\\Niagara4.11\\JENEsys"
```

This will generate ``HotWaterTempReset.bog`` in the provided path.  The
top‑level folder in the .bog is named ``HotWaterTempReset`` to match
Workbench conventions.
"""

from __future__ import annotations

import argparse
import os
import sys

# Attempt to import the installed bog_builder package.  If running this
# example from a source checkout (``src`` layout), adjust sys.path
try:
    from bog_builder import BogFolderBuilder  # type: ignore
except ImportError:
    # Fallback: assume we're running from the repository root
    sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))
    from bog_builder.builder import BogFolderBuilder  # type: ignore


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
    parser = argparse.ArgumentParser(description="Generate a hot water reset .bog file.")
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