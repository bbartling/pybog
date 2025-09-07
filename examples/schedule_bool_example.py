"""
Generate a .bog file with a detailed Boolean schedule.

The schedule has the following behavior:
- Active window (True): 06:00–18:00
- Default (False): All other times
- Applies Sun–Fri, empty on Saturday
"""

from __future__ import annotations

import argparse
import os
from bog_builder import BogFolderBuilder
import copy


def build_boolean_schedule_example(output_directory: str) -> str:
    """Builds and saves a .bog file with a single detailed boolean schedule."""
    builder = BogFolderBuilder("Schedules_Example", debug=True)

    # --- 1. Common Schedule Structure ---
    # This dictionary defines the "always effective" date range and the weekly
    # time blocks.
    common_schedule_structure = {
        "effective": {
            "start": {
                "yearSchedule": {"alwaysEffective": True},
                "monthSchedule": {"singleSelection": True},
                "daySchedule": {"singleSelection": True},
                "weekdaySchedule": {"singleSelection": True},
            },
            "end": {
                "yearSchedule": {"alwaysEffective": True},
                "monthSchedule": {"singleSelection": True},
                "daySchedule": {"singleSelection": True},
                "weekdaySchedule": {"singleSelection": True},
            },
        },
        "schedule": {
            "specialEvents": {},
            "week": {
                "sunday": {
                    "day": {"time": {"start": "06:00:00.000", "finish": "18:00:00.000"}}
                },
                "monday": {
                    "day": {"time": {"start": "06:00:00.000", "finish": "18:00:00.000"}}
                },
                "tuesday": {
                    "day": {"time": {"start": "06:00:00.000", "finish": "18:00:00.000"}}
                },
                "wednesday": {
                    "day": {"time": {"start": "06:00:00.000", "finish": "18:00:00.000"}}
                },
                "thursday": {
                    "day": {"time": {"start": "06:00:00.000", "finish": "18:00:00.000"}}
                },
                "friday": {
                    "day": {"time": {"start": "06:00:00.000", "finish": "18:00:00.000"}}
                },
                "saturday": {"day": {}},  # Empty day
            },
        },
    }

    # --- 2. Boolean Schedule ---
    # Use a deep copy to avoid modifying the original structure if reused
    boolean_props = copy.deepcopy(common_schedule_structure)
    boolean_props.update(
        {"defaultOutput": {"value": False}, "out": {"value": True}}  # Current value
    )
    # Add the specific boolean value for the active time blocks
    for day in boolean_props["schedule"]["week"].values():
        if day["day"].get("time"):
            day["day"]["time"]["effectiveValue"] = {"value": True}

    builder.add_boolean_schedule("BooleanSchedule", properties=boolean_props)
    builder.add_boolean_writable("BooleanWritable")
    builder.add_link("BooleanSchedule", "out", "BooleanWritable", "in16")

    # --- 3. Save the file ---
    os.makedirs(output_directory, exist_ok=True)
    out_path = os.path.join(output_directory, "BooleanSchedule.bog")
    builder.save(out_path)
    return out_path


def main() -> None:
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Generate a .bog file with a detailed boolean schedule."
    )
    parser.add_argument(
        "-o",
        "--output",
        default="examples",
        help="Directory to write the .bog file (default: examples).",
    )
    args = parser.parse_args()

    out_path = build_boolean_schedule_example(args.output)
    print(f"Successfully created schedule example at: {out_path}")


if __name__ == "__main__":
    main()
