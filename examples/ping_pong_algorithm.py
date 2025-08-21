"""
This script builds a robust "ping-pong" or oscillating counter.
The core of the logic is a counter that automatically increments up to a top limit,
then decrements down to a low limit, and repeats this cycle continuously.

This example is fundamentally important for understanding Guideline 36 (G36)
style trim-and-respond algorithms. The key mechanism is a `BooleanLatch` which
acts as a state machine, remembering whether the system is currently in a
"counting up" or "counting down" state. This stateful, incremental adjustment
is the basis for complex G36 sequences like VAV damper pressure optimization
or chilled water temperature resets.

Key Components:
- A central Counter that holds the current value.
- A MultiVibrator that provides a steady pulse for incrementing/decrementing.
- A BooleanLatch that stores the current counting direction (Up vs. Down).
- Limit checkers (GreaterThanEqual, LessThanEqual) that trigger the change in direction.
- Gating logic (And, Not) to ensure the pulse is routed to either the 'countUp'
  or 'countDown' slot based on the latch's state.
"""


import sys, os, argparse

from bog_builder import BogFolderBuilder


def main():
    p = argparse.ArgumentParser(description="Build a robust Ping-Pong Counter .bog file.")
    p.add_argument("-o","--output_dir", default="examples", help="Output directory for the .bog file.")
    p.add_argument("-n","--name", default="PingPongCounter")
    p.add_argument("-s","--subfolder", default="Logic")
    args = p.parse_args()

    script_filename = os.path.basename(__file__).replace(".py", "")
    builder = BogFolderBuilder(args.name)

    # --- Top-Level Components ---
    # These are the user-facing controls and displays.
    builder.add_numeric_writable("CounterViewer", 0.0) 
    builder.add_numeric_writable("Step", 1.0) 
    builder.add_numeric_writable("TopLimit", 20.0) 
    builder.add_numeric_writable("LowLimit", -20.0) 
    builder.add_boolean_writable("ManualResetCounter", default_value=False) 

    # --- Logic Sub-Folder ---
    # All calculation logic is placed in a sub-folder for organization.
    builder.start_sub_folder(args.subfolder) 

    # Core components for timing and counting
    # CORRECTED: Changed period from "2s" to "2000" to adhere to millisecond format [cite: 3, 4]
    builder.add_component("kitControl:MultiVibrator", "MultiViber", properties={"period": "2000"}) 
    builder.add_component("kitControl:Counter", "Counter") 
    
    # One-shots to ensure single increments/decrements per pulse
    builder.add_component("kitControl:OneShot", "IncrementUpOneShot") 
    builder.add_component("kitControl:OneShot", "IncrementDownOneShot") 
    builder.add_component("kitControl:OneShot", "ResetOneShot") 
    
    # Limit-checking logic
    builder.add_component("kitControl:GreaterThanEqual", "AtOrAbove_TopLimit") 
    builder.add_component("kitControl:LessThanEqual", "AtOrBelow_LowLimit") 

    # --- State-Holding and Gating Logic (The Fix) ---
    # A BooleanLatch holds the direction state: False=Up, True=Down.
    builder.add_component("kitControl:BooleanLatch", "IsCountingDown_Latch") 
    builder.add_component("kitControl:Not", "IsNotCountingDown_Not") # Inverter for up-counting logic 
    builder.add_component("kitControl:And", "UpPulse_Gate") # Gate for enabling up-counts 
    builder.add_component("kitControl:And", "DownPulse_Gate") # Gate for enabling down-counts 
    
    builder.end_sub_folder()

    # --- Wiring ---
    print("Wiring components...")

    # Wire the main counter properties and reset
    builder.add_link("Step", "out", "Counter", "countIncrement") 
    builder.add_link("Counter", "out", "CounterViewer", "in16") 
    builder.add_link("ManualResetCounter", "out", "ResetOneShot", "in") 
    builder.add_link("ResetOneShot", "out", "Counter", "clear") 

    # Wire the counter's current value to the limit checkers
    builder.add_link("Counter", "out", "AtOrAbove_TopLimit", "inA") 
    builder.add_link("TopLimit", "out", "AtOrAbove_TopLimit", "inB") 
    builder.add_link("Counter", "out", "AtOrBelow_LowLimit", "inA") 
    builder.add_link("LowLimit", "out", "AtOrBelow_LowLimit", "inB") 

    # --- State-Management Wiring ---
    # Set the latch to 'True' (is counting down) when the top limit is reached.
    builder.add_link("AtOrAbove_TopLimit", "out", "IsCountingDown_Latch", "set") 
    # Reset the latch to 'False' (is counting up) when the low limit is reached.
    builder.add_link("AtOrBelow_LowLimit", "out", "IsCountingDown_Latch", "reset") 

    # --- Pulse Gating Wiring ---
    # Logic to enable the up-counting pulse:
    builder.add_link("IsCountingDown_Latch", "out", "IsNotCountingDown_Not", "in") 
    builder.add_link("IsNotCountingDown_Not", "out", "UpPulse_Gate", "inA") # Must NOT be counting down 
    builder.add_link("MultiViber", "out", "UpPulse_Gate", "inB")             # AND a pulse is active 
    builder.add_link("UpPulse_Gate", "out", "IncrementUpOneShot", "in") 
    builder.add_link("IncrementUpOneShot", "out", "Counter", "countUp") 

    # Logic to enable the down-counting pulse:
    builder.add_link("IsCountingDown_Latch", "out", "DownPulse_Gate", "inA") # Must BE counting down 
    builder.add_link("MultiViber", "out", "DownPulse_Gate", "inB")            # AND a pulse is active 
    builder.add_link("DownPulse_Gate", "out", "IncrementDownOneShot", "in") 
    builder.add_link("IncrementDownOneShot", "out", "Counter", "countDown") 
    
    # --- Save the File ---
    bog_filename = f"{script_filename}.bog"
    output_path = os.path.join(args.output_dir, bog_filename)
    os.makedirs(args.output_dir, exist_ok=True)
    builder.save(output_path)
    print(f"\nSuccessfully created Niagara .bog file at: {output_path}")

if __name__ == "__main__":
    main()