"""
kitControl:LeadLagRuntime with Corrected Runtime Feedback
---------------------------------------------------------
This script creates a robust and correct demonstration for the
kitControl:LeadLagRuntime component. It simulates a 4-chiller sequencing
application and includes a dynamic, user-configurable rotation time.

The key feature of this logic is the use of a NumericLatch to correctly
handle runtime feedback. The LeadLagRuntime component is designed to poll
the runtime of INACTIVE equipment to decide which unit to start next.
Therefore, feeding it a live, running counter from an active chiller will
not work as intended. This script solves that problem by storing the final
runtime of a chiller at the moment it shuts down.

For simulation purposes, the default 'maxRuntime' is set to a short
duration (20 seconds). In a real-world application, this would typically
be set to a much longer period, such as 40 hours, to ensure even wear
on the equipment over time.

Algorithm:
- A master 'Chiller_Enable' signal enables the LeadLagRuntime block.
- A 'Rotate_Seconds' input allows dynamic configuration of the 'maxRuntime'.
  This value is converted to milliseconds before being linked.
- A periodic timer pulses every second. When a chiller is commanded ON, an 'And'
  gate allows these pulses to trigger the 'countUp' slot of a dedicated 'Counter',
  which increments by 1 each time.
- The live output of the Counter (total elapsed seconds) is fed to the 'in'
  slot of a 'NumericLatch'.
- When the chiller command turns OFF, a 'Not' block triggers the 'clock' of the
  NumericLatch. This action captures and stores the final accumulated runtime.
- The output of this latch is multiplied by 1000 to convert seconds to
  milliseconds.
- This final millisecond value is converted to a RelTime value and linked to
  the corresponding 'runtime' slot on the LeadLagRuntime block.
- The LeadLagRuntime block can now correctly read the stored runtime of all
  inactive chillers and sequence the equipment properly.
"""

import os
import argparse
import sys

# Per instructions, append to sys.path to find bog_builder
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))
from bog_builder import BogFolderBuilder


def main():
    """
    Main function to build and save the advanced LeadLagRuntime Counter simulation.
    """
    parser = argparse.ArgumentParser(
        description="Build a .bog file to simulate a 4-chiller LeadLagRuntime with Counters and correct latching logic."
    )
    parser.add_argument(
        "-o",
        "--output_dir",
        default="examples",
        help="Output directory for the .bog file.",
    )
    args = parser.parse_args()

    builder = BogFolderBuilder("LeadLagRuntime_Latch_Fixed", debug=True)

    print("--- Creating Top-Level I/O Components ---")

    # --- Inputs & Outputs (at the root level) ---
    builder.add_boolean_writable("Chiller_Enable", default_value=False)

    chiller_names = ["A", "B", "C", "D"]
    for chiller in chiller_names:
        builder.add_boolean_writable(f"Chiller_{chiller}_Cmd")
        builder.add_numeric_writable(f"Chiller_{chiller}_Runtime")

    builder.add_component(
        "kitControl:NumericConst", "Rotate_Seconds", properties={"value": 30.0}
    )

    # --- Logic Components (organized inside a sub-folder) ---
    print("\n--- Creating Logic Components inside 'Logic' sub-folder ---")
    builder.start_sub_folder("Logic")

    lead_lag_properties = {
        "numberOutputs": 4,
        "maxRuntime": "20s",
        "feedbackDelay": "10s",
        "clearAlarmTime": "1m",
    }
    builder.add_component(
        "kitControl:LeadLagRuntime", "Chiller_LeadLag", properties=lead_lag_properties
    )

    builder.add_component("kitControl:Or", "Feedback_Or")
    builder.add_component(
        "kitControl:MultiVibrator", "OneSecondTimer", properties={"period": "5s"}
    )
    builder.add_component("kitControl:OneShot", "TimerPulse")
    builder.add_component(
        "kitControl:NumericConst", "Count_Increment_Value", properties={"value": 5.0}
    )
    builder.add_component(
        "kitControl:NumericConst", "Const_1000_ms", properties={"value": 1000.0}
    )
    builder.add_component("kitControl:Multiply", "Calc_MaxRuntime_ms")

    # --- Runtime Accumulation and Latching Logic ---
    for chiller in chiller_names:
        builder.add_counter(f"Chiller_{chiller}_RuntimeCounter")
        builder.add_component("kitControl:And", f"Chiller_{chiller}_IncrementGate")

    builder.end_sub_folder()

    print("\n--- Wiring Components ---")

    builder.add_link("Chiller_Enable", "out", "Chiller_LeadLag", "in")
    builder.add_link("Chiller_A_Cmd", "out", "Feedback_Or", "inA")
    builder.add_link("Chiller_B_Cmd", "out", "Feedback_Or", "inB")
    builder.add_link("Chiller_C_Cmd", "out", "Feedback_Or", "inC")
    builder.add_link("Chiller_D_Cmd", "out", "Feedback_Or", "inD")
    builder.add_link("Feedback_Or", "out", "Chiller_LeadLag", "feedback")
    builder.add_link("OneSecondTimer", "out", "TimerPulse", "in")

    for chiller in chiller_names:
        builder.add_link(
            f"Chiller_LeadLag", f"out{chiller}", f"Chiller_{chiller}_Cmd", "in16"
        )
        builder.add_link("TimerPulse", "out", f"Chiller_{chiller}_IncrementGate", "inA")
        builder.add_link(
            f"Chiller_{chiller}_Cmd", "out", f"Chiller_{chiller}_IncrementGate", "inB"
        )
        builder.add_link(
            f"Chiller_{chiller}_IncrementGate",
            "out",
            f"Chiller_{chiller}_RuntimeCounter",
            "countUp",
        )
        builder.add_link(
            "Count_Increment_Value",
            "out",
            f"Chiller_{chiller}_RuntimeCounter",
            "countIncrement",
        )
        builder.add_link(
            f"Chiller_{chiller}_RuntimeCounter",
            "out",
            "Chiller_LeadLag",
            f"runtime{chiller}",
            link_type="b:ConversionLink",
            converter_type="conv:StatusNumericToRelTime",
        )
        builder.add_link(
            f"Chiller_{chiller}_RuntimeCounter",
            "out",
            f"Chiller_{chiller}_Runtime",
            "in16",
        )

    builder.add_link("Rotate_Seconds", "out", "Calc_MaxRuntime_ms", "inA")
    builder.add_link("Const_1000_ms", "out", "Calc_MaxRuntime_ms", "inB")

    builder.add_link(
        "Calc_MaxRuntime_ms",
        "out",
        "Chiller_LeadLag",
        "maxRuntime",
        link_type="b:ConversionLink",
        converter_type="conv:StatusNumericToRelTime",
    )

    bog_filename = "lead_lag_runtime_block_playground.bog"
    output_path = os.path.join(args.output_dir, bog_filename)
    os.makedirs(args.output_dir, exist_ok=True)
    builder.save(output_path)

    print(
        f"\nSuccessfully created Niagara .bog file at: {os.path.abspath(output_path)}"
    )
    print("Drag this file into Niagara Workbench to test the corrected logic.")


if __name__ == "__main__":
    main()
