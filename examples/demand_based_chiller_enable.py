"""
Please generate a BOG for a chiller enable/disable sequence that is driven by the 
maximum cooling valve position across 10 AHUs. The logic should first chain the max 
blocks together to determine the highest valve position. The chiller should enable 
when this maximum valve exceeds 30 percent, and once enabled it should remain on 
until the maximum valve falls below 15 percent, at which point it should disable. 
This behavior should act like a latch: enabling above 30 percent and disabling 
only after the value drops below 15 percent. To prevent short cycling, include 
a 30-minute off-delay before enabling and a 15-minute on-delay before disabling. 
The final output should drive a Boolean writable point that represents the chiller enable command.
"""

import os
import argparse
from pathlib import Path
from bog_builder import BogFolderBuilder


def build_bog(output_dir: Path, bog_filename: str) -> Path:
    """Build the .bog and return the absolute path to the saved file."""
    builder = BogFolderBuilder("ChillerEnableLogic", debug=False)

    # --- Define Inputs and Final Output ---
    # Create 10 numeric writable points to simulate AHU cooling valve positions.
    input_names = []
    for i in range(1, 11):
        name = f"AHU_{i:02d}_Cooling_Valve"
        input_names.append(name)
        # Stagger default values for easier testing.
        builder.add_numeric_writable(name, default_value=float(0))

    builder.add_boolean_writable("Chiller_Enable_Command", default_value=True)

    builder.add_reduction_block(
        block_type="Maximum",
        final_output_name="Max_Cooling_Valve",
        input_names=input_names
    )

    # --- Core Control Logic Sub-Folder ---
    builder.start_sub_folder("ControlLogic")

    # Define the setpoints for enabling and disabling the chiller.
    builder.add_component(
        "kitControl:NumericConst",
        "Enable_Setpoint",
        properties={"value": 30.0}
    )
    builder.add_component(
        "kitControl:NumericConst",
        "Disable_Setpoint",
        properties={"value": 15.0}
    )

    # Comparison blocks to check if the max valve position crosses the setpoints.
    builder.add_component("kitControl:GreaterThan", "Check_Enable_Condition")
    builder.add_component("kitControl:LessThan", "Check_Disable_Condition")

    # Latching logic to hold the chiller request state.
    builder.add_component("kitControl:Or", "State_Change_Trigger")
    builder.add_component("kitControl:BooleanLatch", "Chiller_Request_Latch")

    # offDelay: 30 minutes (1,800,000 ms) before disabling.
    delay_properties = {
        "offDelay": "1800000"
    }
    builder.add_component(
        "kitControl:BooleanDelay",
        "Anti_Short_Cycle_Delay",
        properties=delay_properties
    )

    builder.end_sub_folder()

    # --- Wiring the Logic ---

    # Wire max valve and setpoints to comparison blocks.
    builder.add_link("Max_Cooling_Valve", "out", "Check_Enable_Condition", "inA")
    builder.add_link("Enable_Setpoint", "out", "Check_Enable_Condition", "inB")
    builder.add_link("Max_Cooling_Valve", "out", "Check_Disable_Condition", "inA")
    builder.add_link("Disable_Setpoint", "out", "Check_Disable_Condition", "inB")

    # Wire comparison outputs to the latching logic.
    builder.add_link("Check_Enable_Condition", "out", "State_Change_Trigger", "inA")
    builder.add_link("Check_Disable_Condition", "out", "State_Change_Trigger", "inB")

    builder.add_link("Check_Enable_Condition", "out", "Chiller_Request_Latch", "in")
    builder.add_link("State_Change_Trigger", "out", "Chiller_Request_Latch", "clock")

    # Wire the latched request to the time delay block.
    builder.add_link("Chiller_Request_Latch", "out", "Anti_Short_Cycle_Delay", "in")

    # Wire the final, time-delayed output to the command point.
    builder.add_link("Anti_Short_Cycle_Delay", "out", "Chiller_Enable_Command", "in16")

    # --- Save the .bog File ---
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / bog_filename
    builder.save(str(out_path))

    return out_path.resolve()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a .bog file for chiller enable/disable logic driven by the max of 10 AHU cooling valve positions."
    )
    parser.add_argument(
        "-o", "--output_dir",
        default="examples",
        help="Output directory for the .bog file (default: %(default)s)."
    )
    parser.add_argument(
        "-n", "--name",
        default=None,
        help="Base name for the .bog (default: script filename)."
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # Derive script base name (without .py). Fallback to 'chiller_enable' if unknown.
    script_filename = os.path.basename(__file__).replace(".py", "")
    base_name = args.name or (script_filename if script_filename else "chiller_enable")
    bog_filename = f"{base_name}.bog"

    output_dir = Path(args.output_dir)

    print("[INFO] Building BOG ...")
    print(f"[INFO]  output_dir = {output_dir}")
    print(f"[INFO]  bog_name   = {bog_filename}")

    out_path = build_bog(output_dir, bog_filename)

    print("[SUCCESS] Successfully created Niagara .bog file.")
    print(f"[SUCCESS] Full path: {out_path}")


if __name__ == "__main__":
    main()
