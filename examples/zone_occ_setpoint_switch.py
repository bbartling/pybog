import sys
import os
import argparse

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.bog_builder import BogFolderBuilder


def main():
    parser = argparse.ArgumentParser(
        description="Zone Occupancy Setpoint Switching (Direct) .bog file."
    )
    parser.add_argument(
        "-o", "--output_dir", default="examples", help="Output directory."
    )
    args = parser.parse_args()

    builder = BogFolderBuilder("Zone_Occ_Setpoint_Switch", debug=True)

    # Inputs
    builder.add_boolean_writable(
        "Occ_Schedule", default_value=False
    )  # Occupied (True) / Unoccupied (False)
    builder.add_numeric_writable(
        "Occ_Zone_Setpoint", default_value=72.0
    )  # Occupied cooling temp (°F)
    builder.add_numeric_writable(
        "Unocc_Zone_Setpoint", default_value=78.0
    )  # Unoccupied cooling temp (°F)

    # Logic Components
    builder.add_numeric_switch(
        "Zone_Setpoint_Switch"
    )  # Switch between occupied/unoccupied setpoints

    # Output
    builder.add_numeric_writable("Zone_Temp_SPt")  # Final Zone Setpoint

    # Wiring:
    # Pipe Occ_Schedule Boolean directly into NumericSwitch
    builder.add_link("Occ_Schedule", "out", "Zone_Setpoint_Switch", "inSwitch")
    builder.add_link("Occ_Zone_Setpoint", "out", "Zone_Setpoint_Switch", "inTrue")
    builder.add_link("Unocc_Zone_Setpoint", "out", "Zone_Setpoint_Switch", "inFalse")

    # Final output setpoint
    builder.add_link("Zone_Setpoint_Switch", "out", "Zone_Temp_SPt", "in16")

    # Save file
    output_path = os.path.join(args.output_dir, "zone_occ_setpoint_switch.bog")
    os.makedirs(args.output_dir, exist_ok=True)
    builder.save(output_path)
    print(f"Successfully created {output_path}")


if __name__ == "__main__":
    main()
