"""

"""


import os
import argparse

from bog_builder import BogFolderBuilder


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-o",
        "--output_dir",
    )
    args = parser.parse_args()

    script_filename = os.path.basename(__file__).replace(".py", "")

    builder = BogFolderBuilder("BogSubFolderPlayground")
    print("Creating top-level inputs and outputs...")

    builder.start_sub_folder("One")
    builder.end_sub_folder()

    builder.start_sub_folder("Two")
    builder.end_sub_folder()

    builder.start_sub_folder("Three")
    builder.end_sub_folder()

    builder.start_sub_folder("Four")
    builder.end_sub_folder()

    builder.start_sub_folder("Five")
    builder.end_sub_folder()




    bog_filename = f"{script_filename}.bog"
    output_path = os.path.join(args.output_dir, bog_filename)
    os.makedirs(args.output_dir, exist_ok=True)
    builder.save(output_path)
    print(f"\nSuccessfully created Niagara .bog file at: {output_path}")


if __name__ == "__main__":
    main()
