"""
Custom Ping-Pong Algorithm (G36 Style)

This script implements a robust "ping-pong" or oscillating counter using
fundamental logic blocks, avoiding the kitControl:Counter component. This
is a reliable pattern for creating custom accumulators and control logic.

Its also the fundamnental building blocks to G36 T&R algorithms on real hvac.

Algorithm Overview:
1.  When 'Enable' goes true, a startup delay begins.
2.  During this delay, the output is held at the 'InitialValue'.
3.  After the delay, the main logic is enabled.
4.  A periodic timer pulses every 'UpdateIntervalSeconds'.
5.  On each pulse, the logic adds or subtracts the 'Step' value from the
    current output. The direction is determined by a BooleanLatch.
6.  When the output hits the 'UpperLimit' or 'LowerLimit', the
    BooleanLatch flips, reversing the counting direction.
7.  The core of the logic is a NumericLatch which acts as the memory,
    storing the accumulated value between pulses.
"""

import sys, os, argparse
from bog_builder import BogFolderBuilder


def main():
    p = argparse.ArgumentParser(
        description="Custom ping-pong counter using a NumericLatch."
    )
    p.add_argument("-o", "--output_dir", default="examples")
    args = p.parse_args()

    script_filename = os.path.basename(__file__).replace(".py", "")

    b = BogFolderBuilder("PingPongAlgorithm")

    # --- Top-level I/O and Configuration ---
    b.add_boolean_writable("Enable", default_value=False)
    b.add_numeric_writable("InitialValue", default_value=1.0, precision=2)
    b.add_numeric_writable("UpperLimit", default_value=5.0, precision=2)
    b.add_numeric_writable("LowerLimit", default_value=-5.0, precision=2)
    b.add_numeric_writable("Step", default_value=0.25, precision=2)
    b.add_numeric_writable("UpdateIntervalSeconds", default_value=1.0)
    b.add_numeric_writable("StartupDelaySeconds", default_value=5.0)
    b.add_numeric_writable("OutputViewer", 0.0, precision=2)

    # --- Logic Components ---
    b.start_sub_folder("Logic")

    # State Management (Startup Delay)
    # Calculate default onDelay from StartupDelaySeconds input (default 5 seconds)
    default_startup_delay_ms = str(int(5.0 * 1000))

    b.add_component(
        "kitControl:BooleanDelay",
        "StartupDelay",
        properties={"onDelay": default_startup_delay_ms, "offDelay": "0"},
    )
    b.add_component("kitControl:And", "RunLogicEnable")
    b.add_component(
        "kitControl:NumericConst", "Const_1000", properties={"value": 1000.0}
    )
    b.add_component("kitControl:Multiply", "Delay_ms_Calc")

    # Update Timer
    default_period_ms = "1000"

    b.add_component(
        "kitControl:MultiVibrator",
        "UpdateTimer",
        properties={"period": default_period_ms},
    )
    b.add_component("kitControl:Multiply", "Update_ms_Calc")
    b.add_component("kitControl:OneShot", "UpdatePulse")
    b.add_component("kitControl:And", "PulseGate")

    # Custom Counter Core
    b.add_component("kitControl:NumericLatch", "ValueLatch")
    b.add_component("kitControl:Add", "AddStep")
    b.add_component("kitControl:Subtract", "SubtractStep")
    b.add_numeric_switch("DirectionSwitch")
    b.add_numeric_switch("FinalOutputSwitch")

    # Direction Control Logic
    b.add_component("kitControl:GreaterThanEqual", "HitUpperLimit")
    b.add_component("kitControl:LessThanEqual", "HitLowerLimit")
    b.add_component("kitControl:Or", "HitAnyLimit")
    b.add_component("kitControl:BooleanLatch", "DirectionLatch")

    b.end_sub_folder()

    # --- Wiring ---

    # State Management & Startup Delay
    b.add_link("Enable", "out", "StartupDelay", "in")
    b.add_link("StartupDelaySeconds", "out", "Delay_ms_Calc", "inA")
    b.add_link("Const_1000", "out", "Delay_ms_Calc", "inB")
    b.add_link(
        "Delay_ms_Calc",
        "out",
        "StartupDelay",
        "onDelay",
        link_type="b:ConversionLink",
        converter_type="conv:StatusNumericToRelTime",
    )
    b.add_link("Enable", "out", "RunLogicEnable", "inA")
    b.add_link("Enable", "out", "UpdateTimer", "enabled")
    b.add_link("StartupDelay", "out", "RunLogicEnable", "inB")

    # Timer
    b.add_link("UpdateIntervalSeconds", "out", "Update_ms_Calc", "inA")
    b.add_link("Const_1000", "out", "Update_ms_Calc", "inB")
    b.add_link(
        "Update_ms_Calc",
        "out",
        "UpdateTimer",
        "period",
        link_type="b:ConversionLink",
        converter_type="conv:StatusNumericToRelTime",
    )
    b.add_link("UpdateTimer", "out", "UpdatePulse", "in")
    b.add_link("UpdatePulse", "out", "PulseGate", "inA")
    b.add_link("RunLogicEnable", "out", "PulseGate", "inB")

    # Limit Detection (feedback from final output)
    b.add_link("FinalOutputSwitch", "out", "HitUpperLimit", "inA")
    b.add_link("UpperLimit", "out", "HitUpperLimit", "inB")
    b.add_link("FinalOutputSwitch", "out", "HitLowerLimit", "inA")
    b.add_link("LowerLimit", "out", "HitLowerLimit", "inB")

    # Direction Latching
    b.add_link("HitUpperLimit", "out", "HitAnyLimit", "inA")
    b.add_link("HitLowerLimit", "out", "HitAnyLimit", "inB")
    b.add_link("HitAnyLimit", "out", "DirectionLatch", "clock")
    b.add_link(
        "HitUpperLimit", "out", "DirectionLatch", "in"
    )  # Count down when we hit the top

    # Calculation Logic
    b.add_link("FinalOutputSwitch", "out", "AddStep", "inA")
    b.add_link("Step", "out", "AddStep", "inB")
    b.add_link("FinalOutputSwitch", "out", "SubtractStep", "inA")
    b.add_link("Step", "out", "SubtractStep", "inB")

    # Direction Selection
    b.add_link("DirectionLatch", "out", "DirectionSwitch", "inSwitch")
    b.add_link(
        "SubtractStep", "out", "DirectionSwitch", "inTrue"
    )  # If latch is true (hit top), subtract
    b.add_link(
        "AddStep", "out", "DirectionSwitch", "inFalse"
    )  # If latch is false (hit bottom), add

    # Latching the new value
    b.add_link("DirectionSwitch", "out", "ValueLatch", "in")
    b.add_link("PulseGate", "out", "ValueLatch", "clock")

    # Final Output Selection
    b.add_link("RunLogicEnable", "out", "FinalOutputSwitch", "inSwitch")
    b.add_link("ValueLatch", "out", "FinalOutputSwitch", "inTrue")
    b.add_link("InitialValue", "out", "FinalOutputSwitch", "inFalse")

    # Wire to Viewer
    b.add_link("FinalOutputSwitch", "out", "OutputViewer", "in16")

    # Save
    bog_filename = f"{script_filename}.bog"
    output_path = os.path.join(args.output_dir, bog_filename)
    os.makedirs(args.output_dir, exist_ok=True)
    b.save(output_path)


if __name__ == "__main__":
    main()
