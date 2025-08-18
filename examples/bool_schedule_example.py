
from __future__ import annotations

import argparse
import os
import sys


from src.bog_builder import BogFolderBuilder


def build_bool_schedule(output_directory: str) -> str:
    """Build a minimal boolean schedule and save it as a `.bog` file."""
    builder = BogFolderBuilder("Schedules_Bool", debug=False)
    # Create a boolean schedule component (always True)
    # Using the schedule palette component type.  We provide a default
    # ``out`` property value via properties to ensure it starts in the
    # ``True`` state when imported.
    builder.add_component(
        "sch:BooleanSchedule",
        "BooleanSchedule",
        properties={"out": {"value": True}},
    )
    # Create a BooleanWritable to act on the schedule's output
    builder.add_boolean_writable("BooleanWritable")
    # Link the schedule output to the writable's input.  ``in16`` is used for
    # BooleanWritable targets by convention.
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