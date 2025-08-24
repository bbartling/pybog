# ping_pong_interval_latch.py
"""
Ping-Pong counter (Guideline 36 trim/respond pattern) laid out like the screenshots:
- Top-level: ManualReset, Enabled, Step, TopLimit, LowLimit, Output
- Subfolder 'Logic': Interval pulse -> OneShot -> And(Enabled) -> BooleanSwitch gates
- BooleanLatch flips direction at limits; pulse is routed to countUp / countDown
"""

import os, argparse
from bog_builder import BogFolderBuilder


SCRIPT_BOG_NAME = "PingPongIntervalLatch.bog"
LOGIC_FOLDER = "Logic"

def main():
    p = argparse.ArgumentParser(description="Generate a Niagara .bog: ping-pong counter with Interval + Latch.")
    p.add_argument("-o", "--output_dir", default="examples", help="Directory to write the .bog file.")
    args = p.parse_args()

    b = BogFolderBuilder("PingPongAlgorithm", debug=True)

    # ----- Top-level knobs & displays -----
    b.add_boolean_writable("ManualReset", default_value=False)
    b.add_boolean_writable("Enabled", default_value=True)
    b.add_numeric_writable("Step", default_value=1.05)
    b.add_numeric_writable("TopLimit", default_value=20.0)
    b.add_numeric_writable("LowLimit", default_value=-20.0)
    b.add_numeric_writable("Output")

    # ----- Logic subfolder to mirror your layout -----
    b.start_sub_folder(LOGIC_FOLDER)

    b.add_component("kitControl:MultiVibrator", "Interval", properties={"period": "2000"})
    b.add_component("kitControl:OneShot", "FireOneShot")
    b.add_component("kitControl:And", "EnabledGate")

    # Core counter
    b.add_component("kitControl:Counter", "Counter")

    # Limit checks
    b.add_component("kitControl:GreaterThanEqual", "GreaterThanEq")
    b.add_component("kitControl:LessThanEqual", "LessThanEq")
    b.add_component("kitControl:Or", "Or_LimitHit")

    # Direction latch (True = counting DOWN)
    b.add_component("kitControl:BooleanLatch", "BooleanLatch")
    b.add_component("kitControl:Not", "Not_CountingDown")  # for up path switch

    # Boolean gates to steer pulses to up/down based on latch
    b.add_component("kitControl:BooleanSwitch", "CountDown")
    b.add_component("kitControl:BooleanSwitch", "CountUp")

    # Convenience constants for the switch "false" path
    b.add_component("kitControl:BooleanConst", "BoolFalse", properties={"out": False})

    # Single reset edge for manual clear
    b.add_component("kitControl:OneShot", "ResetOneShot")

    b.end_sub_folder()

    # Interval -> OneShot -> AND(Enabled)
    b.add_link("Interval", "out", "FireOneShot", "in")
    b.add_link("FireOneShot", "out", "EnabledGate", "inA")
    b.add_link("Enabled", "out", "EnabledGate", "inB")

    # Counter increment / display / manual clear
    b.add_link("Step", "out", "Counter", "countIncrement")
    b.add_link("ManualReset", "out", "ResetOneShot", "in")
    b.add_link("ResetOneShot", "out", "Counter", "clear")

    # Limit checks from current Counter value
    b.add_link("Counter", "out", "GreaterThanEq", "inA")
    b.add_link("TopLimit", "out", "GreaterThanEq", "inB")
    b.add_link("Counter", "out", "LessThanEq", "inA")
    b.add_link("LowLimit", "out", "LessThanEq", "inB")

    # Detect either limit; toggle/drive the latch via clock (like your screenshot pattern)
    b.add_link("GreaterThanEq", "out", "Or_LimitHit", "inA")
    b.add_link("LessThanEq", "out", "Or_LimitHit", "inB")
    b.add_link("GreaterThanEq", "out", "BooleanLatch", "set")
    b.add_link("LessThanEq", "out", "BooleanLatch", "reset")
    b.add_link("Or_LimitHit", "out", "BooleanLatch", "clock")

    # Derive "up" selector by inverting latch (True=down ⇒ False=up)
    b.add_link("BooleanLatch", "out", "Not_CountingDown", "in")

    # Gate the pulse to DOWN path when latch True
    b.add_link("BooleanLatch", "out", "CountDown", "inSwitch")
    b.add_link("EnabledGate", "out", "CountDown", "inTrue")
    b.add_link("BoolFalse", "out", "CountDown", "inFalse")
    b.add_link("CountDown", "out", "Counter", "countDown")

    # Gate the pulse to UP path when latch False
    b.add_link("Not_CountingDown", "out", "CountUp", "inSwitch")
    b.add_link("EnabledGate", "out", "CountUp", "inTrue")
    b.add_link("BoolFalse", "out", "CountUp", "inFalse")
    b.add_link("CountUp", "out", "Counter", "countUp")

    b.add_link("Counter", "out", "Output", "in16")

    # ----- Save -----
    os.makedirs(args.output_dir, exist_ok=True)
    out_path = os.path.join(args.output_dir, SCRIPT_BOG_NAME)
    b.save(out_path)
    print(f"Created Niagara .bog at: {os.path.abspath(out_path)}")


if __name__ == "__main__":
    main()
