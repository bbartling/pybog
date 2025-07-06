# examples/main_builder_chiller_plant.py
import sys
import os

# This allows the script to find the 'src' directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.bog_builder import BogFolderBuilder

# --- How to Run ---
# python examples/main_builder_chiller_plant.py
# ------------------

def create_chiller_plant_wiresheet_logic():
    """
    Generates a sophisticated 8-chiller plant sequencer BOG file
    using only standard kitControl wire sheet components.
    """
    builder = BogFolderBuilder('Chiller_Plant_Sequencer_KitControl')
    
    # --- Configure Auto-Layout ---
    builder.x_offset = 140      # Set horizontal distance between blocks
    builder.y_offset = 80       # Set vertical distance for new rows
    builder.wrap_at_x = 450     # Start a new row after this x-coordinate

    print("--- Building Chiller Plant Logic with kitControl blocks ---")

    # --- 1. Create Input and Setpoint Components ---
    print("Adding input and setpoint components...")
    chws_temp = builder.add_component('control:NumericWritable', 'ChilledWaterSupplyTemp', properties={'fallback': '50.0'})
    chw_sp = builder.add_component('control:NumericWritable', 'ChilledWaterSetpoint', properties={'fallback': '44.0'})
    
    # Use a Tstat block to create a simple staging signal based on temperature
    staging_thermostat = builder.add_component(
        'kitControl:Tstat', 'StagingTstat',
        properties={
            'diff': '8.0', 
            'action': 'kitControl:TstatAction.direct' # FIX: Use full enum format
        }
    )
    
    # Create a Ramp to convert the boolean staging signal into a 0-100% demand
    staging_ramp = builder.add_component(
        'kitControl:Ramp', 'StagingRamp',
        properties={'period': '00:02:00'} # 2-minute ramp time
    )
    
    builder.new_row()

    # --- 2. Create the Main Sequencer ---
    print("Adding the main staging sequencer...")
    
    sequencer = builder.add_component(
        'kitControl:SequenceLinear', 'ChillerSequencer',
        properties={
            'numberOutputs': '8',
            'action': 'kitControl:SequenceAction.rotating', # FIX: Use full enum format
            'delay': '00:00:10',
            'rotateTime': '24:00:00'
        }
    )
    builder.new_row()

    # --- 3. Create Logic for Each Chiller ---
    print("Adding individual logic for 8 chillers...")
    
    for i in range(1, 9):
        # Input for this chiller's alarm status
        alarm_input = builder.add_component('control:BooleanWritable', f'Chiller{i}_Alarm')
        
        # Invert the alarm signal (since we want to enable if NOT alarmed)
        alarm_not = builder.add_component('kitControl:Not', f'Chiller{i}_NotAlarmed')

        # AND gate: Sequencer must call for run AND chiller must not be alarmed
        permission_and = builder.add_component('kitControl:And', f'Chiller{i}_Permission')

        # Delay block to enforce minimum run time
        min_run_time = builder.add_component(
            'kitControl:BooleanDelay', f'Chiller{i}_MinRunTime',
            properties={'onDelay': '00:15:00'} # 15-minute minimum on-time
        )
        
        # Final output command for this chiller
        run_cmd_output = builder.add_component('control:BooleanWritable', f'Chiller{i}_RunCmd')
        
        # --- Link this chiller's logic together ---
        builder.add_link(alarm_input.get('h'), 'out', alarm_not.get('h'), 'in')
        builder.add_link(sequencer.get('h'), f'out{chr(ord("A") + i - 1)}', permission_and.get('h'), 'inA')
        builder.add_link(alarm_not.get('h'), 'out', permission_and.get('h'), 'inB')
        builder.add_link(permission_and.get('h'), 'out', min_run_time.get('h'), 'in')
        builder.add_link(min_run_time.get('h'), 'out', run_cmd_output.get('h'), 'in10')

        builder.new_row()


    # --- 4. Link the Main Staging Logic ---
    print("Linking main staging components...")
    builder.add_link(chws_temp.get('h'), 'out', staging_thermostat.get('h'), 'cv')
    builder.add_link(chw_sp.get('h'), 'out', staging_thermostat.get('h'), 'sp')
    builder.add_link(staging_thermostat.get('h'), 'out', staging_ramp.get('h'), 'enable')
    builder.add_link(staging_ramp.get('h'), 'out', sequencer.get('h'), 'in')


    # --- 5. Save the final BOG file ---
    OUTPUT_FILE = 'examples/generated_chiller_plant_kitcontrol.bog'
    builder.save(OUTPUT_FILE)

    print(f"\nGenerated a sophisticated chiller plant sequence in '{OUTPUT_FILE}'.")
    print("This version uses only standard kitControl components.")


if __name__ == "__main__":
    create_chiller_plant_wiresheet_logic()
