import sys
import os
import argparse

# Add the 'src' directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from src.bog_builder_new import BogFolderBuilder

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Build a .bog file for a simple thermostat demo in Niagara 4.",
        epilog="This script generates a Niagara .bog file with thermostat logic."
    )
    parser.add_argument(
        "-o", "--output_dir", default="examples", help="Output directory for the .bog file."
    )
    args = parser.parse_args()

    # Initialize the builder
    builder = BogFolderBuilder("Thermostat_Demo", debug=False)

    # Add top-level writables for inputs and outputs
    builder.add_numeric_writable("SpaceTemp", default_value=70.0)
    builder.add_numeric_writable("HeatSP", default_value=68.0)
    builder.add_numeric_writable("CoolSP", default_value=78.0)
    builder.add_numeric_writable("Hysteresis", default_value=1.0)
    builder.add_numeric_writable("Mode", default_value=0.0)  # 0=Off, 1=Heat, 2=Cool
    builder.add_boolean_writable("FanAuto", default_value=True)
    builder.add_boolean_writable("Output_HeatCmd", default_value=False)
    builder.add_boolean_writable("Output_CoolCmd", default_value=False)
    builder.add_boolean_writable("Output_FanCmd", default_value=False)

    # Start the Logic subfolder
    builder.start_sub_folder("Logic")

    # Add components for constants
    builder.add_component("kitControl:NumericConst", "Const_1", properties={"value": 1.0})
    builder.add_component("kitControl:NumericConst", "Const_2", properties={"value": 2.0})

    # Add components for Mode equality checks
    builder.add_component("kitControl:Equal", "Mode_Equal_1")
    builder.add_component("kitControl:Equal", "Mode_Equal_2")

    # Add components for Heat logic
    builder.add_component("kitControl:Subtract", "Subtract_Heat")
    builder.add_component("kitControl:LessThan", "LessThan_Heat")
    builder.add_component("kitControl:And", "And_Heat")

    # Add components for Cool logic
    builder.add_component("kitControl:Add", "Add_Cool")
    builder.add_component("kitControl:GreaterThan", "GreaterThan_Cool")
    builder.add_component("kitControl:And", "And_Cool")

    # Add components for Fan logic
    builder.add_component("kitControl:Not", "Not_FanAuto")
    builder.add_component("kitControl:Or", "Or_HeatCool")
    builder.add_component("kitControl:Or", "Or_Fan")

    # End the Logic subfolder
    builder.end_sub_folder()

    # Add links for Mode equality
    builder.add_link("Mode", "out", "Mode_Equal_1", "inA")
    builder.add_link("Const_1", "out", "Mode_Equal_1", "inB")
    builder.add_link("Mode", "out", "Mode_Equal_2", "inA")
    builder.add_link("Const_2", "out", "Mode_Equal_2", "inB")

    # Add links for Heat logic
    builder.add_link("HeatSP", "out", "Subtract_Heat", "inA")
    builder.add_link("Hysteresis", "out", "Subtract_Heat", "inB")
    builder.add_link("SpaceTemp", "out", "LessThan_Heat", "inA")
    builder.add_link("Subtract_Heat", "out", "LessThan_Heat", "inB")
    builder.add_link("Mode_Equal_1", "out", "And_Heat", "inA")
    builder.add_link("LessThan_Heat", "out", "And_Heat", "inB")

    # Add links for Cool logic
    builder.add_link("CoolSP", "out", "Add_Cool", "inA")
    builder.add_link("Hysteresis", "out", "Add_Cool", "inB")
    builder.add_link("SpaceTemp", "out", "GreaterThan_Cool", "inA")
    builder.add_link("Add_Cool", "out", "GreaterThan_Cool", "inB")
    builder.add_link("Mode_Equal_2", "out", "And_Cool", "inA")
    builder.add_link("GreaterThan_Cool", "out", "And_Cool", "inB")

    # Add links for Fan logic
    builder.add_link("FanAuto", "out", "Not_FanAuto", "in")
    builder.add_link("And_Heat", "out", "Or_HeatCool", "inA")
    builder.add_link("And_Cool", "out", "Or_HeatCool", "inB")
    builder.add_link("Not_FanAuto", "out", "Or_Fan", "inA")
    builder.add_link("Or_HeatCool", "out", "Or_Fan", "inB")

    # Link logic outputs to output writables
    builder.add_link("And_Heat", "out", "Output_HeatCmd", "in16")
    builder.add_link("And_Cool", "out", "Output_CoolCmd", "in16")
    builder.add_link("Or_Fan", "out", "Output_FanCmd", "in16")

    # Save the .bog file
    os.makedirs(args.output_dir, exist_ok=True)
    out_path = os.path.join(args.output_dir, "thermostat_demo.bog")
    builder.save(out_path)
    print(f"Created Niagara .bog at: {out_path}")