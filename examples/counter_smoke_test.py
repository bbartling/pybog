"""
A minimal "smoke test" for the Counter component. This script sets up a
basic, self-resetting counter. A MultiVibrator provides a regular pulse
which increments the counter. After each pulse, a BooleanDelay is triggered,
which then clears the counter after a 3-second delay. This is useful for
verifying the basic functionality of the Counter and Delay blocks.
"""

import sys, os, argparse

from bog_builder import BogFolderBuilder


def main():
    p = argparse.ArgumentParser(description="Minimal Counter smoke test (.bog).")
    p.add_argument("-o", "--output_dir", default="examples")
    p.add_argument("-n", "--name", default="CounterSmoke")
    p.add_argument("-s", "--subfolder", default="Logic")
    args = p.parse_args()

    b = BogFolderBuilder(args.name)

    # Display and knobs
    b.add_numeric_writable("CounterViewer", 0.0, precision=0)  # just to see the count
    b.add_component("kitControl:NumericConst", "Inc", properties={"out": 1.0})

    # Logic
    b.start_sub_folder(args.subfolder)
    b.add_multi_vibrator("Pulse", period_ms="2000")
    b.add_component("kitControl:OneShot", "PulseEdge")
    b.add_component(
        "kitControl:BooleanDelay",
        "Delay",
        properties={"onDelay": "3000", "offDelay": "0"},
    )
    b.add_counter("C", count_increment=1.0, initial_value=0.0)

    # Wire it
    b.add_link("Pulse", "out", "PulseEdge", "in")  # periodic rising edge
    b.add_link("PulseEdge", "out", "C", "countUp")  # increment counter
    b.add_link("Inc", "out", "C", "countIncrement")  # 1 per pulse
    b.add_link("C", "out", "CounterViewer", "in10")  # visualize (pick your slot)
    b.add_link("PulseEdge", "out", "Delay", "in")  # start a clear delay after a tick
    b.add_link("Delay", "out", "C", "clear")  # clear action after delay
    b.end_sub_folder()

    os.makedirs(args.output_dir, exist_ok=True)
    out = os.path.join(args.output_dir, "counter_smoke_test.bog")
    b.save(out)
    print(f"Created {out}")


if __name__ == "__main__":
    main()
