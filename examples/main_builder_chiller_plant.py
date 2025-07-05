# examples/main_builder_chiller_plant.py
import sys
import os

# This allows the script to find the 'src' directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.bog_builder import BogFolderBuilder

# --- How to Run ---
# python examples/main_builder_chiller_plant.py
# ------------------

def create_chiller_plant_logic():
    """
    Generates a sophisticated 8-chiller plant sequencer BOG file.
    """
    builder = BogFolderBuilder('Chiller_Plant_Sequencer')
    builder.x_offset = 160  # Give a bit more space for these blocks

    print("--- Building Chiller Plant Logic ---")

    # --- 1. Create Input Points ---
    print("Adding input components...")
    
    # Main system inputs
    sys_enable = builder.add_component('control:BooleanWritable', 'SystemEnable', properties={'fallback': 'true'})
    chws_temp = builder.add_component('control:NumericWritable', 'ChilledWaterSupplyTemp', properties={'fallback': '50.0'})
    chwr_temp = builder.add_component('control:NumericWritable', 'ChilledWaterReturnTemp', properties={'fallback': '60.0'})
    chw_sp = builder.add_component('control:NumericWritable', 'ChilledWaterSetpoint', properties={'fallback': '44.0'})
    
    builder.new_row()
    
    # Create alarm inputs and run command outputs for all 8 chillers in a loop
    chiller_alarms = []
    chiller_run_cmds = []
    
    for i in range(1, 9):
        # Add alarm input
        alarm_comp = builder.add_component('control:BooleanWritable', f'Chiller{i}_Alarm')
        chiller_alarms.append(alarm_comp)
        
        # Add run command output on a new row
        builder.new_row()
        run_cmd_comp = builder.add_component('control:BooleanWritable', f'Chiller{i}_RunCmd')
        chiller_run_cmds.append(run_cmd_comp)
        builder.new_row()


    # --- 2. Define the Java Logic for the Program Object ---
    # This Java code will be embedded directly into the Program object's 'execute' slot.
    java_logic = """
// Member variables to hold the state for each chiller
long[] lastStartTime = new long[8];
long[] lastStopTime = new long[8];
boolean[] isRunning = new boolean[8];

public void onStart() throws Exception {
    // Initialize all states on startup
    for (int i = 0; i < 8; i++) {
        lastStartTime[i] = 0;
        lastStopTime[i] = 0;
        isRunning[i] = false;
        getChillerEnable(i + 1).setValue(false);
    }
    getLeadChiller().setValue(1);
    updateTimer();
}

public void onExecute() throws Exception {
    updateTimer();

    // If system is disabled, shut everything down.
    if (!getSystemEnable().getValue()) {
        for (int i = 0; i < 8; i++) {
            getChillerEnable(i + 1).setValue(false);
            isRunning[i] = false;
        }
        getStatusTrace().setValue("System Disabled.");
        return;
    }

    // --- Get Inputs ---
    double chwsTemp = getChwsTemp().getValue();
    double setpoint = getChwSetpoint().getValue();
    double tempError = chwsTemp - setpoint;
    int leadChiller = (int) getLeadChiller().getValue();
    long minRunTimeMillis = (long) (getMinRunTimeMinutes().getValue() * 60 * 1000);
    
    // --- Staging Logic ---
    int requiredChillers = 0;
    if (tempError > 1.0) requiredChillers = 1;
    if (tempError > 3.0) requiredChillers = 2;
    if (tempError > 5.0) requiredChillers = 3;
    if (tempError > 7.0) requiredChillers = 4;
    // ... continue for more stages if needed up to 8
    
    getRequiredChillers().setValue(requiredChillers);

    // --- Rotation and Execution Logic ---
    boolean[] chillerAlarms = getChillerAlarms();
    boolean[] nextEnableState = new boolean[8];
    int enabledCount = 0;
    long now = System.currentTimeMillis();

    // First, lock in any chillers that MUST keep running due to min-run-time
    for (int i = 0; i < 8; i++) {
        if (isRunning[i] && (now - lastStartTime[i] < minRunTimeMillis)) {
            nextEnableState[i] = true;
            enabledCount++;
        }
    }

    // Now, iterate through the duty cycle to bring on additional chillers if needed
    if (enabledCount < requiredChillers) {
        for (int i = 0; i < 8; i++) {
            if (enabledCount >= requiredChillers) break;
            
            int chillerIndex = (leadChiller - 1 + i) % 8;
            
            // Check if this chiller is available and not already locked on
            if (!chillerAlarms[chillerIndex] && !nextEnableState[chillerIndex]) {
                // Check if min-off-time has passed (for simplicity, we assume same as run time)
                if (now - lastStopTime[chillerIndex] >= minRunTimeMillis) {
                    nextEnableState[chillerIndex] = true;
                    enabledCount++;
                }
            }
        }
    }

    // --- Set Final Outputs and Update State Timestamps ---
    int actualEnabled = 0;
    for (int i = 0; i < 8; i++) {
        boolean shouldBeRunning = nextEnableState[i];
        
        if (shouldBeRunning && !isRunning[i]) {
            lastStartTime[i] = now;
        } else if (!shouldBeRunning && isRunning[i]) {
            lastStopTime[i] = now;
        }
        
        isRunning[i] = shouldBeRunning;
        getChillerEnable(i + 1).setValue(shouldBeRunning);
        if(shouldBeRunning) actualEnabled++;
    }
    
    // Rotate lead for next time
    if(requiredChillers == 0 && actualEnabled == 0) {
        getLeadChiller().setValue((leadChiller % 8) + 1);
    }

    getStatusTrace().setValue("Error: " + tempError + "F, Required: " + requiredChillers + ", Enabled: " + actualEnabled);
}

// --- Helper Methods ---
void updateTimer() {
    if (ticket != null) ticket.cancel();
    ticket = Clock.schedule(getComponent(), BRelTime.makeSeconds(15), BProgram.execute, null);
}

BStatusBoolean getChillerEnable(int num) {
    switch(num) {
        case 1: return getChiller1_RunCmd();
        case 2: return getChiller2_RunCmd();
        case 3: return getChiller3_RunCmd();
        case 4: return getChiller4_RunCmd();
        case 5: return getChiller5_RunCmd();
        case 6: return getChiller6_RunCmd();
        case 7: return getChiller7_RunCmd();
        case 8: return getChiller8_RunCmd();
        default: return null;
    }
}

boolean[] getChillerAlarms() {
    return new boolean[] {
        getChiller1_Alarm().getValue(), getChiller2_Alarm().getValue(),
        getChiller3_Alarm().getValue(), getChiller4_Alarm().getValue(),
        getChiller5_Alarm().getValue(), getChiller6_Alarm().getValue(),
        getChiller7_Alarm().getValue(), getChiller8_Alarm().getValue()
    };
}
"""

    # --- 3. Create the Main Program Object ---
    print("Adding Program Object with embedded Java logic...")
    builder.new_row()
    builder._current_x = 400 # Center the main logic block
    builder._current_y = 200

    program_properties = {
        # Inputs
        'systemEnable': 'true',
        'chwsTemp': '50.0',
        'chwSetpoint': '44.0',
        'minRunTimeMinutes': '15.0',
        'chiller1_Alarm': 'false', 'chiller2_Alarm': 'false',
        'chiller3_Alarm': 'false', 'chiller4_Alarm': 'false',
        'chiller5_Alarm': 'false', 'chiller6_Alarm': 'false',
        'chiller7_Alarm': 'false', 'chiller8_Alarm': 'false',
        # Outputs
        'chiller1_RunCmd': 'false', 'chiller2_RunCmd': 'false',
        'chiller3_RunCmd': 'false', 'chiller4_RunCmd': 'false',
        'chiller5_RunCmd': 'false', 'chiller6_RunCmd': 'false',
        'chiller7_RunCmd': 'false', 'chiller8_RunCmd': 'false',
        # Status
        'leadChiller': '1',
        'requiredChillers': '0',
        'statusTrace': 'Ready',
        # The Java Code
        'execute': java_logic
    }

    logic_program = builder.add_component(
        'control:Program', 
        'ChillerSequencingLogic',
        properties=program_properties
    )

    # --- 4. Link everything together ---
    print("Adding links...")
    
    # Link main inputs
    builder.add_link(sys_enable.get('h'), 'out', logic_program.get('h'), 'systemEnable')
    builder.add_link(chws_temp.get('h'), 'out', logic_program.get('h'), 'chwsTemp')
    builder.add_link(chw_sp.get('h'), 'out', logic_program.get('h'), 'chwSetpoint')

    # Link all the chiller alarms and run commands
    for i in range(8):
        # Link alarm input
        builder.add_link(
            chiller_alarms[i].get('h'), 'out',
            logic_program.get('h'), f'chiller{i+1}_Alarm'
        )
        # Link run command output
        builder.add_link(
            logic_program.get('h'), f'chiller{i+1}_RunCmd',
            chiller_run_cmds[i].get('h'), 'in10'
        )

    # --- 5. Save the final BOG file ---
    OUTPUT_FILE = 'examples/generated_chiller_plant.bog'
    builder.save(OUTPUT_FILE)

    print(f"\nGenerated a sophisticated chiller plant sequence in '{OUTPUT_FILE}'.")
    print("Drag this file into a Niagara wire sheet to see the full logic.")


if __name__ == "__main__":
    create_chiller_plant_logic()