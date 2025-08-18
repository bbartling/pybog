
from __future__ import annotations

import argparse
import os
import sys


from bog_builder import BogFolderBuilder


def build_numeric_schedule(output_directory: str) -> str:
    """Build a minimal numeric schedule and save it as a `.bog` file."""
    builder = BogFolderBuilder("Schedules_Numeric", debug=False)
    # Create a numeric schedule.  Provide ``defaultOutput`` so the schedule
    # has a baseline value of 0.0, and set the ``out`` slot to 1.0 so the
    # schedule immediately outputs 1.0 when imported.
    builder.add_component(
        "sch:NumericSchedule",
        "NumericSchedule",
        properties={
            "defaultOutput": {"value": 0.0},
            "out": {"value": 1.0},
        },
    )
    # Target numeric writable to consume the schedule output
    builder.add_numeric_writable("NumericWritable")
    # Connect the schedule's ``out`` slot to the writable's ``in16`` slot
    builder.add_link("NumericSchedule", "out", "NumericWritable", "in16")
    # Write the .bog file
    os.makedirs(output_directory, exist_ok=True)
    out_path = os.path.join(output_directory, "NumericSchedule.bog")
    builder.save(out_path)
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a simple numeric schedule .bog file.")
    parser.add_argument(
        "-o",
        "--output",
        default="examples",
        help="Directory to write the .bog file (defaults to 'examples').",
    )
    args = parser.parse_args()
    path = build_numeric_schedule(args.output)
    print(f"Created {path}")


if __name__ == "__main__":
    main()
