"""
rate_of_change_limiter.py

This script builds a "rate of change limiter" or "slew rate limiter" wiresheet.
This is a common algorithm used in control systems to prevent equipment from
reacting too quickly to a rapidly changing setpoint or process variable.

This enhanced version includes a configurable 'UpdateSeconds' parameter to define
the time delta over which the maximum change is allowed, similar to the pattern
found in the ping_pong_algorithm example.

A TRUE G36 algorithm will combine compontents of rate_of_change_limiter.py and
the ping_pong_algorithm example. Please reference both of these as they are
thoroughly tested!

Algorithm Overview:
-------------------
1.  **Input:** A fast-changing input signal is provided (a SineWave for demonstration).
2.  **Timing:** A periodic timer (MultiVibrator) fires at an interval defined by the
    'UpdateSeconds' writable, creating an "UpdateTick" that drives the calculation.
3.  **Memory:** A NumericLatch holds the value of the rate-limited output from the
    previous cycle.
4.  **Delta Calculation:** The logic calculates the difference (delta) between the
    current input signal and the previous output.
5.  **Clamping:** This delta is clamped between a user-defined positive and negative
    limit (MaxChangePerSecond). This is the core of the rate-limiting logic.
6.  **Output Calculation:** The clamped delta is added to the previous output value
    to produce the new, slew-rate-limited output.
7.  **Memory Update:** The NumericLatch is updated with the new output, preparing it
    for the next cycle.
"""

from __future__ import annotations
import argparse
import os
import sys

# Append project src directory to path for bog_builder import
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))
from bog_builder import BogFolderBuilder


def build_rate_limiter(b: BogFolderBuilder) -> None:
    """Builds the Rate of Change Limiter logic graph with a configurable time delta."""

    # ==========================================================================
    # 1. TOP-LEVEL I/O AND CONFIGURATION
    # ==========================================================================
    b.add_component("kitControl:SineWave", "FastChangingInput")
    b.add_numeric_writable("MaxChangePerSecond", default_value=5.0)

    # New configurable time delta
    update_seconds_default = 5.0
    b.add_numeric_writable("UpdateSeconds", default_value=update_seconds_default)

    b.add_numeric_writable("RateLimitedOutput", default_value=0.0)

    # ==========================================================================
    # 2. ALGORITHM LOGIC (SUB-FOLDER)
    # ==========================================================================
    b.start_sub_folder("RateLimiterLogic")

    # --- Timer for periodic updates ---
    # The initial period is set from the default value.
    b.add_component(
        "kitControl:MultiVibrator",
        "UpdateTimer",
        properties={"period": str(int(update_seconds_default * 1000))},
    )
    b.add_component("kitControl:OneShot", "UpdateTick")

    # --- Visual feedback for timer period in milliseconds ---
    b.add_component(
        "kitControl:NumericConst", "Const_1000", properties={"value": 1000.0}
    )
    b.add_component("kitControl:Multiply", "Update_ms_Display")
    b.add_numeric_writable("CalculatedPeriod_ms")

    # --- Memory to hold the last output value ---
    b.add_component("kitControl:NumericLatch", "PreviousOutput_Latch")

    # --- Calculate the desired change (Delta) ---
    b.add_component("kitControl:Subtract", "CalculateDelta")

    # --- Logic to clamp the change within limits (using Multiply by -1) ---
    b.add_component(
        "kitControl:NumericConst", "Const_Neg_1", properties={"value": -1.0}
    )
    b.add_component("kitControl:Multiply", "CreateNegativeLimit")
    b.add_component("kitControl:Maximum", "Clamp_Low")
    b.add_component("kitControl:Minimum", "Clamp_High")

    # --- Calculate the new rate-limited output ---
    b.add_component("kitControl:Add", "CalculateNewOutput")

    b.end_sub_folder()

    # ==========================================================================
    # 3. WIRING LOGIC
    # ==========================================================================

    # --- Wire the Timer and its configuration display ---
    b.add_link("UpdateSeconds", "out", "Update_ms_Display", "inA")
    b.add_link("Const_1000", "out", "Update_ms_Display", "inB")
    b.add_link("Update_ms_Display", "out", "CalculatedPeriod_ms", "in16")

    # NOTE: As seen in ping_pong_algorithm.py, this link may not allow for live updates
    # of the MultiVibrator's period in the Workbench. The initial value will be set correctly.
    b.add_link("CalculatedPeriod_ms", "out", "UpdateTimer", "Period")

    b.add_link("UpdateTimer", "out", "UpdateTick", "in")

    # --- Wire the Delta Calculation ---
    b.add_link("FastChangingInput", "out", "CalculateDelta", "inA")
    b.add_link("PreviousOutput_Latch", "out", "CalculateDelta", "inB")

    # --- Wire the Clamping Logic ---
    b.add_link("MaxChangePerSecond", "out", "CreateNegativeLimit", "inA")
    b.add_link("Const_Neg_1", "out", "CreateNegativeLimit", "inB")
    b.add_link("CalculateDelta", "out", "Clamp_Low", "inA")
    b.add_link("CreateNegativeLimit", "out", "Clamp_Low", "inB")
    b.add_link("Clamp_Low", "out", "Clamp_High", "inA")
    b.add_link("MaxChangePerSecond", "out", "Clamp_High", "inB")

    # --- Wire the New Output Calculation ---
    b.add_link("PreviousOutput_Latch", "out", "CalculateNewOutput", "inA")
    b.add_link("Clamp_High", "out", "CalculateNewOutput", "inB")

    # --- Wire the Memory Update ---
    b.add_link("CalculateNewOutput", "out", "PreviousOutput_Latch", "in")
    b.add_link("UpdateTick", "out", "PreviousOutput_Latch", "clock")

    # --- Wire the Final Output ---
    b.add_link("CalculateNewOutput", "out", "RateLimitedOutput", "in16")


def main() -> None:
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Build a .bog file for a Rate of Change Limiter algorithm."
    )
    parser.add_argument(
        "-o",
        "--output_dir",
        default="examples",
        help="Directory to write the .bog file.",
    )
    args = parser.parse_args()

    builder = BogFolderBuilder("RateOfChangeLimiter_ConfigurableTime")
    build_rate_limiter(builder)

    output_filename = "rate_of_change_limiter_configurable.bog"

    os.makedirs(args.output_dir, exist_ok=True)
    out_path = os.path.join(args.output_dir, output_filename)
    builder.save(out_path)
    print(f"Successfully created Niagara .bog file at: {os.path.abspath(out_path)}")


if __name__ == "__main__":
    main()
