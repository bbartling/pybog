"""
Ping-Pong Counter Algorithm (MultiVibrator 2s)

G36 trim-and-respond scaffold.
Pay close attention how Bool Switches CountDown And CountUp
is wired to inSwitch slots and wires to respected InFalse on
CountUp and inTrue on CountDown as well as the Bool Latch
Clock and In slots to make the Counter oscillates up to
TopLimit, down to LowLimit, repeat on the 2000 multi vibe
interval.

Why it matters (G36)
- Models stepwise setpoint trim and respond HVAC algorithms for guideline 36.
- Replace limit checks with aggregated “requests”
  (e.g., many zones high → UP; many low → DOWN).

"""

import os, argparse
from bog_builder import BogFolderBuilder


def main():
    ap = argparse.ArgumentParser(description="Ping-pong with MultiVibrator (2s)")
    ap.add_argument(
        "-o", "--output_dir", default="examples", help="Output directory for .bog"
    )
    args = ap.parse_args()

    b = BogFolderBuilder("PingPongAlgorithm", debug=True)

    # ---- Top-level I/O (same labels as your sheet) ----
    b.add_boolean_writable("ManualReset", default_value=False)
    b.add_boolean_writable("Enabled", default_value=True)
    b.add_numeric_writable("Step", default_value=1.05)
    b.add_numeric_writable("TopLimit", default_value=20.0)
    b.add_numeric_writable("LowLimit", default_value=-20.0)
    b.add_numeric_writable("Output")

    # ---- Logic subfolder ----
    b.start_sub_folder("Logic")
    b.add_component(
        "kitControl:MultiVibrator", "MultiVibrator", properties={"period": "2000"}
    )
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

    # ---- Wiring (inside Logic) ----
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
    out = os.path.join(args.output_dir, "ping_pong_multivib.bog")
    b.save(out)
    print(f"Created Niagara .bog at: {os.path.abspath(out)}")


if __name__ == "__main__":
    main()
