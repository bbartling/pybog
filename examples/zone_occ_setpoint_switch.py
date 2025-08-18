import sys
import os
import argparse

from bog_builder import BogFolderBuilder


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

    # --- Inputs ---
    builder.add_boolean_writable("Occ_Schedule", default_value=False)
    builder.add_numeric_writable("Occ_Zone_Setpoint", default_value=72.0)
    builder.add_numeric_writable("Unocc_Zone_Setpoint", default_value=78.0)

    # --- Output ---
    builder.add_numeric_writable("Zone_Temp_SPt")

    builder.start_sub_folder("SetpointLogic")

    builder.add_numeric_switch("Zone_Setpoint_Switch")

    builder.end_sub_folder()

    builder.add_link("Occ_Schedule", "out", "Zone_Setpoint_Switch", "inSwitch")
    builder.add_link("Occ_Zone_Setpoint", "out", "Zone_Setpoint_Switch", "inTrue")
    builder.add_link("Unocc_Zone_Setpoint", "out", "Zone_Setpoint_Switch", "inFalse")

    builder.add_link("Zone_Setpoint_Switch", "out", "Zone_Temp_SPt", "in16")

    bog_filename = f"{script_filename}.bog"
    output_path = os.path.join(args.output_dir, bog_filename)
    os.makedirs(args.output_dir, exist_ok=True)
    builder.save(output_path)
    print(f"\nSuccessfully created Niagara .bog file at: {output_path}")


if __name__ == "__main__":
    main()
