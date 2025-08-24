"""
Generate a simple hard-coded numeric schedule (.bog).

Schedule behavior:
- Active window: 06:00–18:00, value = 1.0
- Default/off-hours: value = 0.0
- Applies Sun–Fri, empty on Saturday
"""

from __future__ import annotations

import argparse
import os
from bog_builder import BogFolderBuilder


def build_numeric_schedule(output_directory: str) -> str:
    builder = BogFolderBuilder("Schedules_Numeric", debug=True)

    # Hard-coded schedule properties (mirrors Workbench "Good.xml")
    props = {
        "defaultOutput": {"value": 0.0},
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
                # Active days: Sun–Fri
                "sunday":    {"day": {"time": {"start": "06:00:00.000",
                                               "finish": "18:00:00.000",
                                               "effectiveValue": {"value": 1.0}}}},
                "monday":    {"day": {"time": {"start": "06:00:00.000",
                                               "finish": "18:00:00.000",
                                               "effectiveValue": {"value": 1.0}}}},
                "tuesday":   {"day": {"time": {"start": "06:00:00.000",
                                               "finish": "18:00:00.000",
                                               "effectiveValue": {"value": 1.0}}}},
                "wednesday": {"day": {"time": {"start": "06:00:00.000",
                                               "finish": "18:00:00.000",
                                               "effectiveValue": {"value": 1.0}}}},
                "thursday":  {"day": {"time": {"start": "06:00:00.000",
                                               "finish": "18:00:00.000",
                                               "effectiveValue": {"value": 1.0}}}},
                "friday":    {"day": {"time": {"start": "06:00:00.000",
                                               "finish": "18:00:00.000",
                                               "effectiveValue": {"value": 1.0}}}},
                # Saturday empty (falls back to defaultOutput)
                "saturday":  {"day": {}},
            },
        },
        "out": {"value": 1.0},
    }

    builder.add_component("sch:NumericSchedule", "NumericSchedule", properties=props)
    builder.add_numeric_writable("NumericWritable")
    builder.add_link("NumericSchedule", "out", "NumericWritable", "in16")

    os.makedirs(output_directory, exist_ok=True)
    out_path = os.path.join(output_directory, "NumericSchedule.bog")
    builder.save(out_path)
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate hard-coded numeric schedule .bog file.")
    parser.add_argument("-o", "--output", default="examples",
                        help="Directory to write the .bog file (default: examples).")
    args = parser.parse_args()

    out_path = build_numeric_schedule(args.output)
    print(f"Created {out_path}")


if __name__ == "__main__":
    main()
