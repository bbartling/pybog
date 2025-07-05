# examples/main_builder_g36.py
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.bog_builder import BogFolderBuilder

# 1. Create a builder for a folder named 'G36_DuctStatic_Reset'
builder = BogFolderBuilder('G36_DuctStatic_Reset')

# 2. Add components. The builder will now place them automatically.
print("Adding components with auto-layout...")
vav_max = builder.add_component(
    'kitControl:Maximum', 'VavDamperMax', 
    properties={'in1': '0.0', 'in2': '0.0', 'in3': '0.0', 'in4': '0.0'}
)

pid_loop = builder.add_component(
    'kitControl:LoopPoint', 'DuctStaticPID',
    properties={'proportionalConstant': '2.0', 'integralConstant': '0.1'}
)

duct_sp_output = builder.add_component(
    'control:NumericWritable', 'DuctStaticSetpoint'
)

# Example of adding another row of logic
builder.new_row() # Move to the next line

fan_status = builder.add_component(
    'control:BooleanWritable', 'FanStatus'
)


# 3. Add links between the components using their handles
print("Adding links...")
builder.add_link(
    source_comp_handle=vav_max.get('h'), source_slot='out',
    target_comp_handle=pid_loop.get('h'), target_slot='controlledVariable'
)

builder.add_link(
    source_comp_handle=pid_loop.get('h'), source_slot='out',
    target_comp_handle=duct_sp_output.get('h'), target_slot='in10'
)


# 4. Save the final result to a .bog file
OUTPUT_FILE = 'examples/generated_g36_logic.bog'
builder.save(OUTPUT_FILE)

print(f"\nGenerated a Guideline 36 sequence in '{OUTPUT_FILE}'.")
print("You can now drag this file into a Niagara wire sheet.")