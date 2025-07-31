import sys
import os
import argparse

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
# Make sure you are importing the new builder with sub-folder capabilities
from src.bog_builder_new import BogFolderBuilder

def main():
    parser = argparse.ArgumentParser(
        description="Zone Occupancy Setpoint Switching (Direct) .bog file."
    )
    parser.add_argument(
        "-o", "--output_dir", default="examples", help="Output directory."
    )
    args = parser.parse_args()

    script_filename = os.path.basename(__file__).replace(".py", "")

    builder = BogFolderBuilder("Zone_Occ_Setpoint_Switch", debug=True)

    # 1. Define all TOP-LEVEL components first.
    # These are the inputs and outputs the user will directly interact with.
    # --- Inputs ---
    builder.add_boolean_writable(
        "Occ_Schedule", default_value=False
    )  # Occupied (True) / Unoccupied (False)
    builder.add_numeric_writable(
        "Occ_Zone_Setpoint", default_value=72.0
    )  # Occupied cooling temp (°F)
    builder.add_numeric_writable(
        "Unocc_Zone_Setpoint", default_value=78.0
    )  # Unoccupied cooling temp (°F)

    # --- Output ---
    builder.add_numeric_writable("Zone_Temp_SPt")  # Final Zone Setpoint


    # TUTORIAL: HOW TO USE SUB-FOLDERS
    # We will place the NumericSwitch block inside a sub-folder to keep the
    # main wiresheet clean and focused on the inputs and final output.

    # STEP 1: Start the sub-folder "sandbox".
    # To see the logic flat for debugging, you can simply comment out this line.
    builder.start_sub_folder("SetpointLogic")

    # --- Logic Component ---
    # This NumericSwitch is now created inside the "SetpointLogic" folder.
    builder.add_numeric_switch(
        "Zone_Setpoint_Switch"
    )  # Switch between occupied/unoccupied setpoints

    # STEP 2: End the sub-folder "sandbox".
    # To see the logic flat for debugging, you can simply comment out this line.
    builder.end_sub_folder()


    # 3. Register all links.
    # No changes are needed here. The builder will automatically create proxies
    # for all links that cross the boundary into or out of "SetpointLogic".

    # Pipe inputs from the top level into the switch inside the sub-folder
    builder.add_link("Occ_Schedule", "out", "Zone_Setpoint_Switch", "inSwitch")
    builder.add_link("Occ_Zone_Setpoint", "out", "Zone_Setpoint_Switch", "inTrue")
    builder.add_link("Unocc_Zone_Setpoint", "out", "Zone_Setpoint_Switch", "inFalse")

    # Pipe the result from the switch inside the sub-folder to the top-level output
    builder.add_link("Zone_Setpoint_Switch", "out", "Zone_Temp_SPt", "in16")

    # 4. Save file
    bog_filename = f"{script_filename}.bog"
    output_path = os.path.join(args.output_dir, bog_filename)
    os.makedirs(args.output_dir, exist_ok=True)
    builder.save(output_path)
    print(f"\nSuccessfully created Niagara .bog file at: {output_path}")


if __name__ == "__main__":
    main()
