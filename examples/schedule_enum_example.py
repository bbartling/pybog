"""
Generate a .bog file with a detailed Enum schedule.

The schedule has the following behavior:
- Default state is "duty1".
- Sun-Fri have an active state from 07:00 to 13:30, with a unique "duty" state for each day.
- Saturday has two active blocks with different "duty" states.
"""

from __future__ import annotations

import argparse
import os
from bog_builder import BogFolderBuilder
import copy


def build_enum_schedule_example(output_directory: str) -> str:
    """Builds and saves a .bog file with a single detailed enum schedule."""
    builder = BogFolderBuilder("Enum_Schedule_Example", debug=True)

    facets_str = "range=E:{duty1=1,duty2=2,duty3=3,duty4=4,duty5=5,duty6=6,duty7=7,duty8=8,duty9=9}"

    # --- 1. Define the Enum Schedule Structure ---
    enum_schedule_props = {
        "facets": facets_str,
        "defaultOutput": {"value": "1"},  # Default to duty1
        "effective": {
            "start": {"yearSchedule": {"alwaysEffective": True}},
            "end": {"yearSchedule": {"alwaysEffective": True}},
        },
        "schedule": {
            "specialEvents": {},
            "week": {
                "sunday": {
                    "day": {
                        "times": [
                            {
                                "start": "07:00:00.000",
                                "finish": "13:30:00.000",
                                "effectiveValue": {"value": "2"},
                            }  # duty2
                        ]
                    }
                },
                "monday": {
                    "day": {
                        "times": [
                            {
                                "start": "07:00:00.000",
                                "finish": "13:30:00.000",
                                "effectiveValue": {"value": "3"},
                            }  # duty3
                        ]
                    }
                },
                "tuesday": {
                    "day": {
                        "times": [
                            {
                                "start": "07:00:00.000",
                                "finish": "13:30:00.000",
                                "effectiveValue": {"value": "4"},
                            }  # duty4
                        ]
                    }
                },
                "wednesday": {
                    "day": {
                        "times": [
                            {
                                "start": "07:00:00.000",
                                "finish": "13:30:00.000",
                                "effectiveValue": {"value": "5"},
                            }  # duty5
                        ]
                    }
                },
                "thursday": {
                    "day": {
                        "times": [
                            {
                                "start": "07:00:00.000",
                                "finish": "13:30:00.000",
                                "effectiveValue": {"value": "6"},
                            }  # duty6
                        ]
                    }
                },
                "friday": {
                    "day": {
                        "times": [
                            {
                                "start": "07:00:00.000",
                                "finish": "13:30:00.000",
                                "effectiveValue": {"value": "7"},
                            }  # duty7
                        ]
                    }
                },
                "saturday": {
                    "day": {
                        "times": [
                            {
                                "start": "02:30:00.000",
                                "finish": "09:00:00.000",
                                "effectiveValue": {"value": "8"},
                            },  # duty8
                            {
                                "start": "14:30:00.000",
                                "finish": "22:30:00.000",
                                "effectiveValue": {"value": "9"},
                            },  # duty9
                        ]
                    }
                },
            },
        },
        "out": {"value": "1"},  # Current value is duty1
    }

    builder.add_enum_schedule("EnumSchedule", properties=enum_schedule_props)
    builder.add_enum_writable("EnumWritable", facets=facets_str, default_value="1")
    builder.add_link("EnumSchedule", "out", "EnumWritable", "in16")

    # --- 2. Save the file ---
    os.makedirs(output_directory, exist_ok=True)
    out_path = os.path.join(output_directory, "EnumSchedule.bog")
    builder.save(out_path)
    return out_path


def main() -> None:
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Generate a .bog file with a detailed enum schedule."
    )
    parser.add_argument(
        "-o",
        "--output",
        default="examples",
        help="Directory to write the .bog file (default: examples).",
    )
    args = parser.parse_args()

    out_path = build_enum_schedule_example(args.output)
    print(f"Successfully created schedule example at: {out_path}")


if __name__ == "__main__":
    main()
