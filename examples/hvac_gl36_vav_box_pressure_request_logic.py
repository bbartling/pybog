"""
This script programmatically builds the VAV Box Static Pressure Request logic
from ASHRAE Guideline 36, §5.6.8.2. It generates a numeric request value
(1, 2, or 3) based on VAV damper command and airflow relative to setpoint.
The logic identifies zones that are struggling to get enough airflow and
generates a request to increase duct static pressure. The final output is
the maximum of all requests.

This script programmatically builds the VAV Box Static Pressure Request logic
from ASHRAE Guideline 36, §5.6.8.2, based on a proven manual design.

It uses multiple sub-folders to cleanly organize the logic for calculations,
each request condition, and final prioritization.
"""

import sys
import os
import argparse

from bog_builder import BogFolderBuilder


def main():

    parser = argparse.ArgumentParser(
        description="Build a .bog file for VAV Static Pressure Request logic."
    )
    parser.add_argument(
        "-o",
        "--output_dir",
        default="examples",
        help="Output directory for the .bog file.",
    )
    args = parser.parse_args()

    script_filename = os.path.basename(__file__).replace(".py", "")

    builder = BogFolderBuilder("G36_VAV_Pressure_Req")
    print("Creating top-level inputs and outputs...")

    # --- Inputs ---
    builder.add_numeric_writable("VavDamperCmd", default_value=96.0)
    builder.add_numeric_writable("VavDamperSpt", default_value=95.0)
    builder.add_numeric_writable("VavFlow", default_value=580.0)
    builder.add_numeric_writable("VavFlowSpt", default_value=970.0)

    # --- Outputs ---
    builder.add_numeric_writable("VAVrequestsTotal")
    print("Creating and organizing logic components in sub-folders...")

    builder.start_sub_folder("PercentageCalculations")
    builder.add_multiply("Calc_50_percent")
    builder.add_multiply("Calc_70_percent")
    builder.add_numeric_const("Const_0_5", properties={"out": 0.5})
    builder.add_numeric_const("Const_0_7", properties={"out": 0.7})
    builder.end_sub_folder()

    builder.start_sub_folder("Generate3RequestsLogic")
    builder.add_less_than("LessThan_Flow_50pct")
    builder.add_greater_than("GreaterThan_Damper_95")
    builder.add_and("Generate3requests")
    builder.add_boolean_delay("Timer_1min_Delay1", on_delay="60000")
    builder.add_numeric_switch("NumericSwitch_3_Req")
    builder.add_numeric_const("Const_3", properties={"out": 3.0})
    builder.end_sub_folder()

    builder.start_sub_folder("Generate2RequestsLogic")
    builder.add_less_than("LessThan_Flow_70pct")
    builder.add_and("Generate2requests")
    builder.add_boolean_delay("Timer_1min_Delay2", on_delay="60000")
    builder.add_numeric_switch("NumericSwitch_2_Req")
    builder.add_numeric_const("Const_2", properties={"out": 2.0})
    builder.end_sub_folder()

    builder.start_sub_folder("Generate1RequestLogic")
    builder.add_boolean_delay("Timer_1min_Delay", on_delay="60000")
    builder.add_numeric_switch("NumericSwitch_1_Req")
    builder.add_numeric_const("Const_1", properties={"out": 1.0})
    builder.end_sub_folder()

    builder.start_sub_folder("Prioritization")
    builder.add_maximum("Maximum")
    builder.end_sub_folder()

    print("Wiring components across all folders...")

    # --- Wire Percentage Calculations ---
    builder.add_link("VavFlowSpt", "out", "Calc_50_percent", "inA")
    builder.add_link("Const_0_5", "out", "Calc_50_percent", "inB")
    builder.add_link("VavFlowSpt", "out", "Calc_70_percent", "inA")
    builder.add_link("Const_0_7", "out", "Calc_70_percent", "inB")

    # --- Wire Logic for 3 Requests ---
    builder.add_link("VavFlow", "out", "LessThan_Flow_50pct", "inA")
    builder.add_link("Calc_50_percent", "out", "LessThan_Flow_50pct", "inB")
    builder.add_link("VavDamperCmd", "out", "GreaterThan_Damper_95", "inA")
    builder.add_link("VavDamperSpt", "out", "GreaterThan_Damper_95", "inB")
    builder.add_link("LessThan_Flow_50pct", "out", "Generate3requests", "inA")
    builder.add_link("GreaterThan_Damper_95", "out", "Generate3requests", "inB")
    builder.add_link("Generate3requests", "out", "Timer_1min_Delay1", "in")
    builder.add_link("Timer_1min_Delay1", "out", "NumericSwitch_3_Req", "inSwitch")
    builder.add_link("Const_3", "out", "NumericSwitch_3_Req", "inTrue")

    # --- Wire Logic for 2 Requests ---
    builder.add_link("VavFlow", "out", "LessThan_Flow_70pct", "inA")
    builder.add_link("Calc_70_percent", "out", "LessThan_Flow_70pct", "inB")
    builder.add_link("LessThan_Flow_70pct", "out", "Generate2requests", "inA")
    builder.add_link("GreaterThan_Damper_95", "out", "Generate2requests", "inB")
    builder.add_link("Generate2requests", "out", "Timer_1min_Delay2", "in")
    builder.add_link("Timer_1min_Delay2", "out", "NumericSwitch_2_Req", "inSwitch")
    builder.add_link("Const_2", "out", "NumericSwitch_2_Req", "inTrue")

    # --- Wire Logic for 1 Request ---
    builder.add_link("GreaterThan_Damper_95", "out", "Timer_1min_Delay", "in")
    builder.add_link("Timer_1min_Delay", "out", "NumericSwitch_1_Req", "inSwitch")
    builder.add_link("Const_1", "out", "NumericSwitch_1_Req", "inTrue")

    # --- Wire Final Prioritization ---
    builder.add_link("NumericSwitch_3_Req", "out", "Maximum", "inA")
    builder.add_link("NumericSwitch_2_Req", "out", "Maximum", "inB")
    builder.add_link("NumericSwitch_1_Req", "out", "Maximum", "inC")
    builder.add_link("Maximum", "out", "VAVrequestsTotal", "in16")

    bog_filename = f"{script_filename}.bog"
    output_path = os.path.join(args.output_dir, bog_filename)
    os.makedirs(args.output_dir, exist_ok=True)
    builder.save(output_path)
    print(f"\nSuccessfully created Niagara .bog file at: {output_path}")


if __name__ == "__main__":
    main()
