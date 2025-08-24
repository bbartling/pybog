"""
This script constructs an improved "ping‑pong" oscillating counter logic for
Niagara 4.  It follows the pattern shown in the provided PingPongGood.xml:

* A periodic interval trigger generates pulses via a OneShot block.
* An And gate combines the pulse with an ``Enabled`` boolean to gate the logic.
* A Counter counts up or down depending on the state of a BooleanLatch.
* GreaterThanEqual and LessThanEqual blocks detect when the counter hits
  configured top and bottom limits.
* An Or combines the two limit signals and drives the latch clock; the
  GreaterThanEqual output drives the latch input.
* Two BooleanSwitch blocks (CountDown and CountUp) route the gated pulse to
  either the ``countDown`` or ``countUp`` input on the Counter based on the
  latch state.

Compared to the original example, this version places all logic inside a
dedicated ``Logic`` subfolder and uses a ``control:TimeTrigger`` instead of a
MultiVibrator.  It also links the reset input via ``clearIn`` and utilises
explicit BooleanSwitch components to steer pulses, mirroring the behaviour seen
in the working PingPongGood XML file.
"""

import os
import argparse

from bog_builder import BogFolderBuilder


def build_ping_pong(output_dir: str) -> str:
    """Construct and save the ping‑pong algorithm .bog.

    Parameters
    ----------
    output_dir : str
        The directory in which the .bog file will be written.

    Returns
    -------
    str
        Absolute path to the generated .bog file.
    """
    builder = BogFolderBuilder("PingPongAlgorithm", debug=True)

    # Top‑level control knobs and display
    builder.add_boolean_writable("ManualReset", default_value=False)
    builder.add_boolean_writable("Enabled", default_value=True)
    builder.add_numeric_writable("Step", 1.05)
    builder.add_numeric_writable("TopLimit", 20.0)
    builder.add_numeric_writable("LowLimit", -20.0)
    builder.add_numeric_writable("Output")

    # Logic subfolder holds all the dynamic components
    builder.start_sub_folder("Logic")
    # Periodic trigger: fires every 2000 ms.  The triggerMode property
    # follows Niagara's IntervalTriggerMode format: ``enabled;start;end;period;mask``.
    builder.add_component(
        "control:TimeTrigger",
        "Interval",
        properties={"triggerMode": "false;00:00:00.000;23:59:59.999;2000;7f"},
    )
    # Edge detector for interval pulses
    builder.add_component("kitControl:OneShot", "FireOneShot")
    # Gate the pulse with the Enabled writable
    builder.add_component("kitControl:And", "And")
    # Numeric counter with configurable increment
    builder.add_component("kitControl:Counter", "Counter")
    # Limit detection
    builder.add_component("kitControl:GreaterThanEqual", "GreaterThanEqual")
    builder.add_component("kitControl:LessThanEqual", "LessThanEqual")
    # Combine limit signals
    builder.add_component("kitControl:Or", "Or1")
    # State machine: remembers whether we're counting up (False) or down (True)
    builder.add_component("kitControl:BooleanLatch", "BooleanLatch1")
    # Route pulses based on the latch state
    builder.add_component("kitControl:BooleanSwitch", "CountDown")
    builder.add_component("kitControl:BooleanSwitch", "CountUp")
    # Manual reset edge detector
    builder.add_component("kitControl:OneShot", "ResetOneShot")

    # --- Wiring ---
    # Step value drives the counter's increment
    builder.add_link("Step", "out", "Counter", "countIncrement")
    # Display counter value at top level
    builder.add_link("Counter", "out", "Output", "in16")
    # Manual reset: trigger a reset pulse and clear the counter
    builder.add_link("ManualReset", "out", "ResetOneShot", "in")
    builder.add_link("ResetOneShot", "out", "Counter", "clearIn")
    # Interval pulse to OneShot (edge detection)
    builder.add_link("Interval", "fireTrigger", "FireOneShot", "in")
    # Gate the edge pulse with the Enabled flag
    builder.add_link("FireOneShot", "out", "And", "inA")
    builder.add_link("Enabled", "out", "And", "inB")
    # Feed counter output to limit detectors
    builder.add_link("Counter", "out", "GreaterThanEqual", "inA")
    builder.add_link("TopLimit", "out", "GreaterThanEqual", "inB")
    builder.add_link("Counter", "out", "LessThanEqual", "inA")
    builder.add_link("LowLimit", "out", "LessThanEqual", "inB")
    # Combine the two limit signals via an OR
    builder.add_link("GreaterThanEqual", "out", "Or1", "inA")
    builder.add_link("LessThanEqual", "out", "Or1", "inB")
    # Boolean latch: clock on either limit event; input true when upper limit hit
    builder.add_link("Or1", "out", "BooleanLatch1", "clock")
    builder.add_link("GreaterThanEqual", "out", "BooleanLatch1", "in")
    # Route pulses to down/up based on latch state
    builder.add_link("And", "out", "CountDown", "inTrue")
    builder.add_link("BooleanLatch1", "out", "CountDown", "inSwitch")
    builder.add_link("And", "out", "CountUp", "inFalse")
    builder.add_link("BooleanLatch1", "out", "CountUp", "inSwitch")
    # Pulse to counter inputs
    builder.add_link("CountDown", "out", "Counter", "countDown")
    builder.add_link("CountUp", "out", "Counter", "countUp")

    # End logic subfolder
    builder.end_sub_folder()

    # Write the .bog file
    os.makedirs(output_dir, exist_ok=True)
    script_name = "fixed_ping_pong_algorithm"
    out_path = os.path.join(output_dir, f"{script_name}.bog")
    builder.save(out_path)
    return os.path.abspath(out_path)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a fixed ping‑pong counter .bog file using Niagara kitControl blocks."
    )
    parser.add_argument(
        "-o",
        "--output_dir",
        default="examples",
        help="Directory in which to place the generated .bog file.",
    )
    args = parser.parse_args()
    out_file = build_ping_pong(args.output_dir)
    print(f"\nGenerated .bog file at: {out_file}")


if __name__ == "__main__":
    main()
