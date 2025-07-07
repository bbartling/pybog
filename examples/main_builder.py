# examples/main_builder.py
import sys
import os
import argparse

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.bog_builder import BogFolderBuilder

def build_g36_sequence(builder):
    """Builds a simple ASHRAE G36 Trim & Respond sequence."""
    print("Building G36 Duct Static Reset sequence...")
    
    vav_max = builder.add_component('kitControl:Maximum', 'VavDamperMax')
    pid_loop = builder.add_component(
        'kitControl:LoopPoint', 'DuctStaticPID',
        properties={'proportionalConstant': '2.0', 'integralConstant': '0.1'}
    )
    duct_sp_output = builder.add_component('control:NumericWritable', 'DuctStaticSetpoint')
    
    builder.add_link(vav_max.get('h'), 'out', pid_loop.get('h'), 'controlledVariable')
    builder.add_link(pid_loop.get('h'), 'out', duct_sp_output.get('h'), 'in10')

def build_chiller_plant(builder):
    """Builds a sophisticated 8-chiller plant sequencer using kitControl blocks."""
    print("Building Chiller Plant Logic with kitControl blocks...")
    
    # Configure Layout
    builder.x_offset = 150
    builder.wrap_at_x = 600

    # Inputs and Staging Logic
    chws_temp = builder.add_component('control:NumericWritable', 'ChilledWaterSupplyTemp', properties={'fallback': '50.0'})
    chw_sp = builder.add_component('control:NumericWritable', 'ChilledWaterSetpoint', properties={'fallback': '44.0'})
    staging_thermostat = builder.add_component(
        'kitControl:Tstat', 'StagingTstat',
        properties={'diff': '8.0', 'action': 'kitControl:TstatAction.direct'}
    )
    builder.new_row()

    # Sequencer
    sequencer = builder.add_component(
        'kitControl:SequenceLinear', 'ChillerSequencer',
        properties={'numberOutputs': '8', 'action': 'kitControl:SequenceAction.rotating', 'delay': '00:00:10'}
    )
    builder.new_row()

    # Per-Chiller Logic Chains
    for i in range(1, 9):
        alarm_input = builder.add_component('control:BooleanWritable', f'Chiller{i}_Alarm')
        alarm_not = builder.add_component('kitControl:Not', f'Chiller{i}_NotAlarmed')
        permission_and = builder.add_component('kitControl:And', f'Chiller{i}_Permission')
        min_run_time = builder.add_component(
            'kitControl:BooleanDelay', f'Chiller{i}_MinRunTime',
            properties={'onDelay': '00:15:00'}
        )
        run_cmd_output = builder.add_component('control:BooleanWritable', f'Chiller{i}_RunCmd')
        
        # Link this chiller's logic chain
        builder.add_link(alarm_input.get('h'), 'out', alarm_not.get('h'), 'in')
        builder.add_link(sequencer.get('h'), f'out{chr(ord("A") + i - 1)}', permission_and.get('h'), 'inA')
        builder.add_link(alarm_not.get('h'), 'out', permission_and.get('h'), 'inB')
        builder.add_link(permission_and.get('h'), 'out', min_run_time.get('h'), 'in')
        builder.add_link(min_run_time.get('h'), 'out', run_cmd_output.get('h'), 'in10')
        builder.new_row()

    # Link Main Staging Logic
    builder.add_link(chws_temp.get('h'), 'out', staging_thermostat.get('h'), 'cv')
    builder.add_link(chw_sp.get('h'), 'out', staging_thermostat.get('h'), 'sp')
    builder.add_link(staging_thermostat.get('h'), 'out', sequencer.get('h'), 'in')

def main():
    parser = argparse.ArgumentParser(description="Build various Niagara .bog files programmatically.")
    parser.add_argument("type", choices=['g36', 'chiller'], help="The type of BOG file to build.")
    parser.add_argument("-o", "--output", default="generated.bog", help="The name of the output file.")
    
    args = parser.parse_args()

    # Create a builder instance with a dynamic name
    folder_name = f"Generated_{args.type.upper()}_Logic"
    builder = BogFolderBuilder(folder_name)

    # Call the appropriate build function based on the type argument
    if args.type == 'g36':
        build_g36_sequence(builder)
    elif args.type == 'chiller':
        build_chiller_plant(builder)
        
    # Save the final result
    builder.save(f"examples/{args.output}")

if __name__ == "__main__":
    main()
