"""
A minimal "smoke test" for the Counter component. This script sets up a
basic, setting an initial value, self-resetting counter. A MultiVibrator provides a regular pulse
which increments the counter. After each pulse, a BooleanDelay is triggered,
which then clears the counter after a 3-second delay. This is useful for
verifying the basic functionality of the Counter and Delay blocks.
"""

import sys, os, argparse

from bog_builder import BogFolderBuilder


def main():
    p = argparse.ArgumentParser(description="Minimal Counter smoke test (.bog).")
    p.add_argument("-o", "--output_dir", default="examples")
    args = p.parse_args()

    b = BogFolderBuilder("CounterSmoke")

    b.add_counter("Counter")
    b.add_numeric_writable("CounterViewer", 0.0, precision=0)
    b.add_numeric_writable("Counter_Preset", default_value=10.0)
    b.add_boolean_writable("CountDown", default_value=False)
    b.add_boolean_writable("CountUp", default_value=False)
    b.add_boolean_writable("Clear", default_value=False)

    # Wire it

    b.add_link("CountUp", "out", "Counter", "countUp")
    b.add_link("CountDown", "out", "Counter", "countDown")

    b.add_link("Clear", "out", "Counter", "clear")
    b.add_link("Counter_Preset", "out", "Counter", "presetValue")


    os.makedirs(args.output_dir, exist_ok=True)
    out = os.path.join(args.output_dir, "counter_smoke_test.bog")
    b.save(out)
    print(f"Created {out}")


if __name__ == "__main__":
    main()
