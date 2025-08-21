import os
from pathlib import Path
from bog_builder import BogFolderBuilder

def build(output_dir: str) -> str | None:
    """
    Generates an HVAC control .bog file for a basic zone control system,
    including occupancy-based setpoint switching and PID temperature control.

    Parameters
    ----------
    output_dir : str
        The directory where the .bog file will be saved. The directory will
        be created if it does not exist.

    Returns
    -------
    str | None
        The full path to the generated .bog file as a string, or None if an
        error occurs (though current implementation aims for robust path handling).
    """
    # Ensure the output directory exists
    output_path_obj = Path(output_dir)
    output_path_obj.mkdir(parents=True, exist_ok=True)

    # Determine the output .bog filename
    bog_name_from_env = os.getenv("BOG_NAME")
    if bog_name_from_env:
        final_bog_path = output_path_obj / bog_name_from_env
    else:
        # Safe default name if BOG_NAME environment variable is not set
        final_bog_path = output_path_obj / "HVAC_Zone_Control_Logic.bog"

    # Ensure the file extension is .bog
    if not str(final_bog_path).lower().endswith(".bog"):
        final_bog_path = final_bog_path.with_suffix(".bog")

    # Initialize the BogFolderBuilder with a descriptive name
    builder = BogFolderBuilder("HVAC_Zone_Control", debug=False)

    # --- 1. Define Top-Level Inputs (Writables) ---
    builder.add_boolean_writable("Occ_Schedule", default_value=False)
    builder.add_numeric_writable("Occ_Zone_Setpoint", default_value=72.0)
    builder.add_numeric_writable("Unocc_Zone_Setpoint", default_value=68.0)
    builder.add_numeric_writable("Zone_Temp", default_value=70.0)
    builder.add_numeric_writable("PID_PropBand", default_value=5.0)
    builder.add_numeric_writable("PID_IntegralTime", default_value=0.05)
    builder.add_boolean_writable("Control_Enable", default_value=True)

    # --- 2. Define Top-Level Outputs (Writables) ---
    builder.add_numeric_writable("Zone_Active_Setpoint")
    builder.add_numeric_writable("Zone_Damper_Command")

    # --- 3. Build Logic Components within Sub-Folders ---

    # Sub-folder for Setpoint Switching Logic
    builder.start_sub_folder("Setpoint_Logic")
    builder.add_numeric_switch("Zone_Setpoint_Switch")
    builder.end_sub_folder()

    # Sub-folder for Temperature PID Control
    builder.start_sub_folder("Temperature_Control")
    # Define LoopPoint properties matching initial writable values for export consistency
    lp_props = {
        "loopEnable": {"value": True},
        "controlledVariable": {"value": 70.0},
        "setpoint": {"value": 72.0},
        "proportionalConstant": {"value": 5.0},
        "integralConstant": {"value": 0.05},
        # For a cooling loop, 'loopAction' default (0 for direct) is typically fine.
        # If it were a heating loop, it might be set to 1 (reverse). Omitting for simplicity.
    }
    builder.add_component("kitControl:LoopPoint", "Zone_Temp_PID", properties=lp_props)
    builder.end_sub_folder()

    # --- 4. Wire Components Together with Links ---

    # Links for Setpoint Switching Logic
    builder.add_link("Occ_Schedule", "out", "Zone_Setpoint_Switch", "inSwitch")
    builder.add_link("Occ_Zone_Setpoint", "out", "Zone_Setpoint_Switch", "inTrue")
    builder.add_link("Unocc_Zone_Setpoint", "out", "Zone_Setpoint_Switch", "inFalse")
    builder.add_link("Zone_Setpoint_Switch", "out", "Zone_Active_Setpoint", "in16")

    # Links for PID Control Logic
    builder.add_link("Control_Enable", "out", "Zone_Temp_PID", "loopEnable")
    builder.add_link("Zone_Temp", "out", "Zone_Temp_PID", "controlledVariable")
    builder.add_link("Zone_Active_Setpoint", "out", "Zone_Temp_PID", "setpoint")
    builder.add_link("PID_PropBand", "out", "Zone_Temp_PID", "proportionalConstant")
    builder.add_link("PID_IntegralTime", "out", "Zone_Temp_PID", "integralConstant")
    builder.add_link("Zone_Temp_PID", "out", "Zone_Damper_Command", "in16")

    # Export the generated logic to the .bog file
    builder.export_to_file(str(final_bog_path))

    return str(final_bog_path)