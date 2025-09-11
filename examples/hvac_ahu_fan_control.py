import os
import argparse
from bog_builder import BogFolderBuilder


def main():
    """
    Human asks via Chat input:

    Can you make an AHU fan duct static pressure control please?
    I need a single PID loop where I can provide a duct static pressure input and a setpoint.
    The loop should be enabled by a fan status signal. The output of the PID loop
    will be the fan speed command. Please expose inputs for the proportional band (P)
    and integral constant (I) for tuning. The control action should be reverse-acting.
    """

    # --- Setup argument parser ---
    parser = argparse.ArgumentParser(
        description="Build an AHU fan duct static pressure control loop (.bog file)."
    )
    parser.add_argument(
        "-o",
        "--output_dir",
        default="examples",
        help="Output directory for the .bog file.",
    )
    args = parser.parse_args()

    # Initialize the BogFolderBuilder with a descriptive name.
    builder = BogFolderBuilder("AHU_Duct_Static_Control", debug=True)

    # --- Define Inputs, Setpoints, and Tuning Parameters ---
    builder.add_numeric_writable("Static_Pressure", default_value=1.2)
    builder.add_numeric_writable("Static_Pressure_Setpoint", default_value=1.5)
    builder.add_boolean_writable("Fan_Status", default_value=True)
    builder.add_boolean_writable("Loop_Action_Direct", default_value=False)
    builder.add_numeric_writable("Proportional_Band", default_value=0.5)
    builder.add_numeric_writable("Integral_Constant", default_value=10.0)

    # --- Define the Output ---
    builder.add_numeric_writable("Fan_Speed_Command", default_value=0.0)

    # --- Define the PID Controller Component ---
    pid_properties = {
        "loopEnable": {"value": True},
        "setpoint": {"value": 1.5},
        "proportionalConstant": {"value": 0.5},
        "integralConstant": {"value": 10.0},
    }
    builder.add_loop_point("Static_Pressure_PID", properties=pid_properties)

    # --- Wire the Components Together ---

    # 1. Wire the process variable (PV) and setpoint (SP) to the PID.
    builder.add_link(
        "Static_Pressure", "out", "Static_Pressure_PID", "controlledVariable"
    )
    builder.add_link(
        "Static_Pressure_Setpoint", "out", "Static_Pressure_PID", "setpoint"
    )

    # 2. Wire the enable signal from Fan_Status to the PID's loopEnable slot.
    builder.add_link("Fan_Status", "out", "Static_Pressure_PID", "loopEnable")

    # 3. Wire the loop action (converts StatusBoolean to FrozenEnum).
    builder.add_link(
        "Loop_Action_Direct",
        "out",
        "Static_Pressure_PID",
        "loopAction",
        link_type="b:ConversionLink",
        converter_type="conv:StatusBooleanToFrozenEnum",
    )

    # 4. Wire the tuning constants (converts StatusNumeric to Number).
    # **** FIX: Re-add explicit conversion link type and converter type ****
    builder.add_link(
        "Proportional_Band",
        "out",
        "Static_Pressure_PID",
        "proportionalConstant",
        link_type="b:ConversionLink",
        converter_type="conv:StatusNumericToNumber",
    )
    builder.add_link(
        "Integral_Constant",
        "out",
        "Static_Pressure_PID",
        "integralConstant",
        link_type="b:ConversionLink",
        converter_type="conv:StatusNumericToNumber",
    )

    # 5. Wire the PID output to the final fan speed command point.
    builder.add_link("Static_Pressure_PID", "out", "Fan_Speed_Command", "in16")

    # --- Save the .bog file ---
    script_filename = "ahu_duct_static_pressure"
    output_filename = f"{script_filename}.bog"
    output_path = os.path.join(args.output_dir, output_filename)
    os.makedirs(args.output_dir, exist_ok=True)
    builder.save(output_path)

    print(f"Successfully created Niagara .bog file at: {output_path}")


if __name__ == "__main__":
    main()
