"""
This script generates a simple boolean schedule. It creates a single
`sch:BooleanSchedule` component and links its output to a BooleanWritable
point. The schedule is configured to be permanently 'True' by default,
making this a useful example for creating basic overrides or enabling flags
that are controlled by a schedule object.
"""


from __future__ import annotations

import argparse
import os
import sys


from src.bog_builder import BogFolderBuilder


def build_bool_schedule(output_directory: str) -> str:
    """Build a minimal boolean schedule and save it as a `.bog` file."""
    builder = BogFolderBuilder("Schedules_Bool", debug=False)
    builder.add_component(
        "sch:BooleanSchedule",
        "BooleanSchedule",
        properties={"out": {"value": True}},
    )
    # Create a BooleanWritable to act on the schedule's output
    builder.add_boolean_writable("BooleanWritable")
    builder.add_link("BooleanSchedule", "out", "BooleanWritable", "in16")
    # Save the archive
    os.makedirs(output_directory, exist_ok=True)
    out_path = os.path.join(output_directory, "BoolSchedule.bog")
    builder.save(out_path)
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a simple boolean schedule .bog file.")
    parser.add_argument(
        "-o",
        "--output",
        default="examples",
        help="Output directory for the .bog file (defaults to 'examples').",
    )
    args = parser.parse_args()
    path = build_bool_schedule(args.output)
    print(f"Created {path}")


if __name__ == "__main__":
    main()