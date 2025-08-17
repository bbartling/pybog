"""Example script for generating a simple boolean schedule.

This script illustrates how to construct a very basic boolean schedule using
``bog_builder``.  In Niagara, schedules are typically represented with
``sch:BooleanSchedule`` objects that can be configured with date and time
patterns.  The builder does not currently provide a high‑level API for
composing the full schedule hierarchy (date ranges, weekly patterns, etc.),
so this example creates a minimal schedule that simply outputs ``True`` at
all times.  It then links the schedule's output to a boolean writable.

To use this as a starting point for a more complex schedule, you could
extend the example by adding properties to the ``BooleanSchedule`` component
or by constructing the schedule tree manually via additional ``add_component``
calls with ``sch:`` types.

Run the script and specify an output directory with ``-o`` to write the
resulting `.bog` file into your Workbench user folder.

Example:

```
python bool_schedule_example.py -o "C:\\Users\\ben\\Niagara4.11\\JENEsys"
```
"""

from __future__ import annotations

import argparse
import os
import sys

try:
    from bog_builder import BogFolderBuilder  # type: ignore
except ImportError:
    # Running from repository checkout
    sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))
    from bog_builder.builder import BogFolderBuilder  # type: ignore


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