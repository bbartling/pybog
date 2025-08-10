import sys, os, argparse
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.bog_builder_new import BogFolderBuilder

def main():
    p = argparse.ArgumentParser(description="Minimal Counter smoke test (.bog).")
    p.add_argument("-o","--output_dir", default="examples")
    p.add_argument("-n","--name", default="PingPongTest")
    p.add_argument("-s","--subfolder", default="Logic")
    args = p.parse_args()

    script_filename = os.path.basename(__file__).replace(".py", "")
    builder = BogFolderBuilder(args.name)

    # Display and knobs
    builder.add_numeric_writable("CounterViewer", 0.0, precision=2)
    builder.add_numeric_writable("Step", 1.55, precision=2)
    builder.add_numeric_writable("TopLimit", 20.00, precision=2)
    builder.add_numeric_writable("LowLimit", -20.00, precision=2)
    builder.add_boolean_writable("ManualResetCounter", default_value=False)

    # Logic
    builder.start_sub_folder(args.subfolder)
    builder.add_multi_vibrator("MultiViber", period_ms="2000")
    builder.add_component("kitControl:OneShot", "IncrementUpOneShot")
    builder.add_component("kitControl:OneShot", "IncrementDownOneShot")
    builder.add_component("kitControl:OneShot", "ResetOneShot")
    builder.add_component("kitControl:GreaterThanEqual", "GreaterThanEqual_Block")
    builder.add_component("kitControl:LessThanEqual", "LessThanEqual_Block")
    builder.add_counter("Counter", count_increment=1.0, initial_value=0.0, precision=2)
    builder.add_component("kitControl:Or", "CountUp_Or_Block")
    builder.add_component("kitControl:And", "CountUp_And_Block")
    builder.add_component("kitControl:Not", "CountDown_Not_Block")
    builder.add_component("kitControl:And", "CountDown_And_Block")

    # Wire it
    builder.add_link("Step", "out", "Counter", "countIncrement")
    builder.add_link("Counter", "out", "CounterViewer", "in16")

    builder.add_link("Counter", "out", "GreaterThanEqual_Block", "inA")
    builder.add_link("TopLimit", "out", "GreaterThanEqual_Block", "inB")

    builder.add_link("Counter", "out", "LessThanEqual_Block", "inA")
    builder.add_link("LowLimit", "out", "LessThanEqual_Block", "inB")

    builder.add_link("ManualResetCounter", "out", "ResetOneShot", "in")
    builder.add_link("ResetOneShot", "out", "Counter", "clear")

    builder.add_link("LessThanEqual_Block", "out", "CountUp_Or_Block", "inA")
    builder.add_link("GreaterThanEqual_Block", "out", "CountDown_Not_Block", "in")
    builder.add_link("CountDown_Not_Block", "out", "CountUp_Or_Block", "inB")
    builder.add_link("CountUp_Or_Block", "out", "CountUp_And_Block", "inA")

    builder.add_link("MultiViber", "out", "CountUp_And_Block", "inB")
    builder.add_link("CountUp_And_Block", "out", "IncrementUpOneShot", "in")
    builder.add_link("IncrementUpOneShot", "out", "Counter", "countUp")

    builder.add_link("MultiViber", "out", "CountDown_And_Block", "inB")
    builder.add_link("CountDown_And_Block", "out", "IncrementDownOneShot", "in")
    builder.add_link("IncrementDownOneShot", "out", "Counter", "countDown") 
    builder.add_link("GreaterThanEqual_Block", "out", "CountDown_And_Block", "inA")

    builder.end_sub_folder()

    bog_filename = f"{script_filename}.bog"
    output_path = os.path.join(args.output_dir, bog_filename)
    os.makedirs(args.output_dir, exist_ok=True)
    builder.save(output_path)
    print(f"\nSuccessfully created Niagara .bog file at: {output_path}")

if __name__ == "__main__":
    main()
