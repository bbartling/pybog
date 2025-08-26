"""
Ping-Pong Counter Algorithm (Configurable Timer)

This script demonstrates a G36-style trim-and-respond scaffold. A counter
oscillates between a high and low limit, driven by a periodic pulse from a
MultiVibrator.

This version includes a top-level NumericWritable 'UpdateSeconds' that is
used to configure the MultiVibrator's period when the .bog file is generated.
The conversion from seconds to milliseconds is also shown on the wiresheet
for documentation purposes.

A TRUE G36 algorithm will combine compontents of rate_of_change_limiter.py and
the ping_pong_algorithm example. Please reference both of these as they are
thoroughly tested!
"""

import os, argparse
from bog_builder import BogFolderBuilder


def main():
    ap = argparse.ArgumentParser(
        description="Ping-pong with a configurable MultiVibrator"
    )
    ap.add_argument(
        "-o", "--output_dir", default="examples", help="Output directory for .bog"
    )
    args = ap.parse_args()

    b = BogFolderBuilder("PingPongAlgorithm", debug=True)

    # ---- Top-level I/O and Configuration ----
    b.add_boolean_writable("ManualReset", default_value=False)
    b.add_boolean_writable("Enabled", default_value=True)
    b.add_numeric_writable("Step", default_value=1.05)
    b.add_numeric_writable("TopLimit", default_value=20.0)
    b.add_numeric_writable("LowLimit", default_value=-20.0)
    b.add_numeric_writable("Output")

    UpdateSeconds_default = 2.0
    b.add_numeric_writable("UpdateSeconds", default_value=UpdateSeconds_default)

    # ---- Logic subfolder ----
    b.start_sub_folder("Logic")
    b.add_component(
        "kitControl:MultiVibrator",
        "MultiVibrator",
        properties={"period": str(int(UpdateSeconds_default * 1000))},
    )
    b.add_component(
        "kitControl:NumericConst", "Const_1000", properties={"value": 1000.0}
    )
    b.add_component("kitControl:Multiply", "Update_ms_Display")
    b.add_numeric_writable("CalculatedPeriod_ms")
    b.add_component("kitControl:OneShot", "FireOneShot")
    b.add_component("kitControl:And", "And")
    b.add_component("kitControl:Counter", "Counter")
    b.add_component("kitControl:GreaterThanEqual", "GreaterThanEq")
    b.add_component("kitControl:LessThanEqual", "LessThanEq")
    b.add_component("kitControl:Or", "Or1")
    b.add_component("kitControl:BooleanLatch", "BooleanLatch")
    b.add_boolean_switch("CountDown")
    b.add_boolean_switch("CountUp")
    b.add_component("kitControl:OneShot", "ResetOneShot")

    b.end_sub_folder()

    # ---- Wiring ----
    b.add_link("UpdateSeconds", "out", "Update_ms_Display", "inA")
    b.add_link("Const_1000", "out", "Update_ms_Display", "inB")
    b.add_link("Update_ms_Display", "out", "CalculatedPeriod_ms", "in16")
    b.add_link(
        "CalculatedPeriod_ms", "out", "MultiVibrator", "Period"
    )  # <------ broken
    b.add_link("MultiVibrator", "out", "FireOneShot", "in")
    b.add_link("FireOneShot", "out", "And", "inA")
    b.add_link("Enabled", "out", "And", "inB")
    b.add_link("Step", "out", "Counter", "countIncrement")
    b.add_link("ManualReset", "out", "ResetOneShot", "in")
    b.add_link("ResetOneShot", "out", "Counter", "clear")
    b.add_link("Counter", "out", "Output", "in16")
    b.add_link("Counter", "out", "GreaterThanEq", "inA")
    b.add_link("TopLimit", "out", "GreaterThanEq", "inB")
    b.add_link("Counter", "out", "LessThanEq", "inA")
    b.add_link("LowLimit", "out", "LessThanEq", "inB")
    b.add_link("GreaterThanEq", "out", "Or1", "inA")
    b.add_link("LessThanEq", "out", "Or1", "inB")
    b.add_link("Or1", "out", "BooleanLatch", "clock")
    b.add_link("GreaterThanEq", "out", "BooleanLatch", "in")
    b.add_link("BooleanLatch", "out", "CountDown", "inSwitch")
    b.add_link("BooleanLatch", "out", "CountUp", "inSwitch")
    b.add_link("And", "out", "CountDown", "inTrue")
    b.add_link("And", "out", "CountUp", "inFalse")
    b.add_link("CountDown", "out", "Counter", "countDown")
    b.add_link("CountUp", "out", "Counter", "countUp")

    # ---- Save ----
    os.makedirs(args.output_dir, exist_ok=True)
    out = os.path.join(args.output_dir, "ping_pong_configurable_timer.bog")
    b.save(out)
    print(f"Created Niagara .bog at: {os.path.abspath(out)}")


if __name__ == "__main__":
    main()
