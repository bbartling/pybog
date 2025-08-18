import sys
import os
import argparse

from bog_builder import BogFolderBuilder


def main():
    parser = argparse.ArgumentParser(description="Build a PulseDelay test .bog file.")
    parser.add_argument(
        "-o", "--output_dir", default="examples", help="Output directory."
    )
    args = parser.parse_args()

    script_filename = os.path.basename(__file__).replace(".py", "")

    # --- Top level ---
    builder = BogFolderBuilder("PulseDelayTest")

    builder.add_boolean_writable(name="Trigger", default_value=False)
    builder.add_boolean_writable(name="Output", default_value=False)

    # --- Subfolder ---
    builder.start_sub_folder("PulseDelay")
    builder.add_component("kitControl:OneShot", "OneShot1")
    builder.add_component(
        "kitControl:BooleanDelay",
        "BooleanDelay",
        properties={"onDelay": "2000", "offDelay": "0"},  # 2-second hold time
    )
    builder.end_sub_folder()

    # --- Wiring ---
    builder.add_link("Trigger", "out", "OneShot1", "in")
    builder.add_link("OneShot1", "out", "BooleanDelay", "in")
    builder.add_link("BooleanDelay", "out", "Output", "in16")

    # Save
    bog_filename = f"{script_filename}.bog"
    output_path = os.path.join(args.output_dir, bog_filename)
    os.makedirs(args.output_dir, exist_ok=True)
    builder.save(output_path)

    print(f"\nSuccessfully created Niagara .bog file at: {output_path}")


if __name__ == "__main__":
    main()
