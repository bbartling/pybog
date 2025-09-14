import os
import argparse
import sys

# The script must append the path to the bog_builder library.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))
from bog_builder import BogFolderBuilder


def main():
    """
    Builds a .bog file demonstrating the built-in kitControl:Psychrometric component.
    """
    parser = argparse.ArgumentParser(
        description="Build a .bog file for a Psychrometric calculation playground."
    )
    parser.add_argument(
        "-o",
        "--output_dir",
        default="examples",
        help="Output directory for the .bog file.",
    )
    args = parser.parse_args()

    builder = BogFolderBuilder("Psychrometric_Playground", debug=True)

    print("--- Creating Inputs and Outputs ---")

    # --- Inputs ---
    builder.add_numeric_writable("Outside_Air_Temp", default_value=80.0, precision=1)
    builder.add_numeric_writable(
        "Outside_Air_Humidity", default_value=50.0, precision=1
    )

    # --- Outputs ---
    builder.add_numeric_writable("Calculated_Dew_Point", default_value=0.0, precision=1)
    builder.add_numeric_writable("Calculated_Enthalpy", default_value=0.0, precision=2)
    builder.add_numeric_writable("Calculated_Wet_Bulb", default_value=0.0, precision=1)

    print("--- Creating Psychrometric Component ---")
    # Use the new, clean helper method
    builder.add_psychrometric("Psychrometric_Calc")

    print("--- Wiring Components Together ---")
    # Wire inputs to the Psychrometric block
    builder.add_link("Outside_Air_Temp", "out", "Psychrometric_Calc", "inTemp")
    builder.add_link("Outside_Air_Humidity", "out", "Psychrometric_Calc", "inHumidity")

    # Wire the desired outputs from the block to their respective display points
    builder.add_link(
        "Psychrometric_Calc", "outDewPoint", "Calculated_Dew_Point", "in16"
    )
    builder.add_link("Psychrometric_Calc", "outEnthalpy", "Calculated_Enthalpy", "in16")
    builder.add_link(
        "Psychrometric_Calc", "outWetBulbTemp", "Calculated_Wet_Bulb", "in16"
    )

    # --- Save the .bog file ---
    bog_filename = "psychrometric_playground.bog"
    output_path = os.path.join(args.output_dir, bog_filename)
    os.makedirs(args.output_dir, exist_ok=True)
    builder.save(output_path)
    print(
        f"\nSuccessfully created Niagara .bog file at: {os.path.abspath(output_path)}"
    )


if __name__ == "__main__":
    main()
