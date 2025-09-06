"""
Intentional bad parse in WB

com.tridium.file.types.bog.CannotLoadBogException: local:|file:~bad_parse_into_wb_example.bog
   at com.tridium.file.types.bog.BBogFile.doOpen(BBogFile.java:461)
   at javax.baja.file.BSubSpaceFile.open(BSubSpaceFile.java:125)
   at com.tridium.file.types.bog.BBogScheme.resolve(BBogScheme.java:56)
   at javax.baja.naming.BOrdScheme.resolve(BOrdScheme.java:107)
   at javax.baja.naming.BOrd.resolve(BOrd.java:274)
   at com.tridium.workbench.shell.BNiagaraWbShell.resolve(BNiagaraWbShell.java:656)
   at com.tridium.workbench.shell.NHyperlinkInfo.resolve(NHyperlinkInfo.java:279)
   at com.tridium.workbench.shell.NHyperlinkInfo.hyperlink(NHyperlinkInfo.java:131)
   at com.tridium.workbench.shell.BNiagaraWbShell.doHyperlink(BNiagaraWbShell.java:515)
   at com.tridium.workbench.shell.BNiagaraWbShell.hyperlink(BNiagaraWbShell.java:473)
   at com.tridium.workbench.file.BDirTable$Controller.hyperlink(BDirTable.java:499)
   at com.tridium.workbench.file.BDirTable$Controller.cellDoubleClicked(BDirTable.java:481)
   at javax.baja.ui.table.TableController.cellPressed(TableController.java:686)
   at javax.baja.ui.table.TableController.mousePressed(TableController.java:261)
   at javax.baja.ui.table.BTable.mousePressed(BTable.java:1517)
   at javax.baja.ui.BWidget.fireMouseEvent(BWidget.java:1227)
   at com.tridium.ui.awt.MouseManager.fire(MouseManager.java:325)
   at com.tridium.ui.awt.MouseManager.fire(MouseManager.java:299)
   at com.tridium.ui.awt.MouseManager.pressed(MouseManager.java:122)
  javax.baja.xml.XException: Invalid Facets: 'units=u:second|precision=i:0|min=d:-inf|max=d:+inf' [33:91]
     at javax.baja.io.ValueDocDecoder$BogDecoderPlugin.err(ValueDocDecoder.java:1367)
     at javax.baja.io.ValueDocDecoder.decodeSimple(ValueDocDecoder.java:901)
     at javax.baja.io.ValueDocDecoder.parseSlot(ValueDocDecoder.java:778)
     at javax.baja.io.ValueDocDecoder.parseSlots(ValueDocDecoder.java:564)
     at javax.baja.io.ValueDocDecoder.parseSlot(ValueDocDecoder.java:826)
     at javax.baja.io.ValueDocDecoder.parseSlots(ValueDocDecoder.java:564)
     at javax.baja.io.ValueDocDecoder.parseSlot(ValueDocDecoder.java:826)
     at javax.baja.io.ValueDocDecoder.parseSlots(ValueDocDecoder.java:564)
     at javax.baja.io.ValueDocDecoder.parseSlot(ValueDocDecoder.java:826)
     at javax.baja.io.ValueDocDecoder.decode(ValueDocDecoder.java:290)
     at javax.baja.io.ValueDocDecoder$BogDecoderPlugin.decodeDocument(ValueDocDecoder.java:1297)
     at javax.baja.io.ValueDocDecoder.decodeDocument(ValueDocDecoder.java:273)
     at javax.baja.io.ValueDocDecoder.decodeDocument(ValueDocDecoder.java:262)
     at com.tridium.file.types.bog.BBogFile.doOpen(BBogFile.java:446)
     at javax.baja.file.BSubSpaceFile.open(BSubSpaceFile.java:125)
     at com.tridium.file.types.bog.BBogScheme.resolve(BBogScheme.java:56)
     at javax.baja.naming.BOrdScheme.resolve(BOrdScheme.java:107)
     at javax.baja.naming.BOrd.resolve(BOrd.java:274)
     at com.tridium.workbench.shell.BNiagaraWbShell.resolve(BNiagaraWbShell.java:656)
    java.io.IOException: second
       at javax.baja.units.BUnit.decodeFromString(BUnit.java:515)
       at javax.baja.data.DataUtil.unmarshal(DataUtil.java:96)
       at javax.baja.sys.BFacets.decodeFromString(BFacets.java:1128)
       at com.tridium.util.SimpleFactory.make(SimpleFactory.java:140)
       at javax.baja.io.ValueDocDecoder.decodeSimple(ValueDocDecoder.java:897)
       at javax.baja.io.ValueDocDecoder.parseSlot(ValueDocDecoder.java:778)
       at javax.baja.io.ValueDocDecoder.parseSlots(ValueDocDecoder.java:564)
       at javax.baja.io.ValueDocDecoder.parseSlot(ValueDocDecoder.java:826)
       at javax.baja.io.ValueDocDecoder.parseSlots(ValueDocDecoder.java:564)
       at javax.baja.io.ValueDocDecoder.parseSlot(ValueDocDecoder.java:826)
       at javax.baja.io.ValueDocDecoder.parseSlots(ValueDocDecoder.java:564)
       at javax.baja.io.ValueDocDecoder.parseSlot(ValueDocDecoder.java:826)
       at javax.baja.io.ValueDocDecoder.decode(ValueDocDecoder.java:290)
       at javax.baja.io.ValueDocDecoder$BogDecoderPlugin.decodeDocument(ValueDocDecoder.java:1297)
       at javax.baja.io.ValueDocDecoder.decodeDocument(ValueDocDecoder.java:273)
       at javax.baja.io.ValueDocDecoder.decodeDocument(ValueDocDecoder.java:262)
       at com.tridium.file.types.bog.BBogFile.doOpen(BBogFile.java:446)
       at javax.baja.file.BSubSpaceFile.open(BSubSpaceFile.java:125)
       at com.tridium.file.types.bog.BBogScheme.resolve(BBogScheme.java:56)
"""

import os
import argparse
from bog_builder import BogFolderBuilder


def main():
    """
    Main function to build and save the advanced LeadLagRuntime Counter simulation.
    """
    parser = argparse.ArgumentParser(
        description="Build a .bog file to simulate a 4-chiller LeadLagRuntime with Counters."
    )
    parser.add_argument(
        "-o",
        "--output_dir",
        default="examples",
        help="Output directory for the .bog file.",
    )
    args = parser.parse_args()

    script_filename = os.path.basename(__file__).replace(".py", "")
    builder = BogFolderBuilder("AdvancedLeadLagRuntime_CounterSim", debug=True)

    print("--- Creating Top-Level I/O Components ---")

    # --- Inputs & Outputs (at the root level) ---
    builder.add_boolean_writable("Chiller_Enable", default_value=False)

    chiller_names = ["A", "B", "C", "D"]
    for chiller in chiller_names:
        builder.add_boolean_writable(f"Chiller_{chiller}_Cmd")
        # Display the accumulated runtime in seconds
        builder.add_numeric_writable(
            f"Chiller_{chiller}_Runtime_Out", units="u:second", precision=0
        )

    # --- Logic Components (organized inside a sub-folder) ---
    print("\n--- Creating Logic Components inside 'Logic' sub-folder ---")
    builder.start_sub_folder("Logic")

    # Core LeadLag component with full properties
    lead_lag_properties = {
        "numberOutputs": 4,
        "maxRuntime": "20s",
        "feedbackDelay": "10s",
        "clearAlarmTime": "1m",
    }
    builder.add_component(
        "kitControl:LeadLagRuntime", "Chiller_LeadLag", properties=lead_lag_properties
    )

    # Feedback logic for four inputs
    builder.add_component("kitControl:Or", "Feedback_Or")

    # --- Runtime Accumulation Logic ---
    for chiller in chiller_names:
        builder.add_counter(f"Chiller_{chiller}_RuntimeCounter")
        builder.add_component("kitControl:And", f"Chiller_{chiller}_RuntimeEnableGate")
        builder.add_numeric_switch(f"Chiller_{chiller}_PulseSwitch")

    # A timer that pulses every second
    builder.add_component(
        "kitControl:MultiVibrator", "OneSecondTimer", properties={"period": "1s"}
    )
    builder.add_component("kitControl:OneShot", "TimerPulse")
    builder.add_component(
        "kitControl:NumericConst", "Const_1", properties={"value": 1.0}
    )

    builder.end_sub_folder()
    print("--- Exited 'Logic' sub-folder ---")

    print("\n--- Wiring Components ---")

    # Wire master enable
    builder.add_link("Chiller_Enable", "out", "Chiller_LeadLag", "in")

    # Wire feedback loop for all four chillers
    builder.add_link("Chiller_A_Cmd", "out", "Feedback_Or", "inA")
    builder.add_link("Chiller_B_Cmd", "out", "Feedback_Or", "inB")
    builder.add_link("Chiller_C_Cmd", "out", "Feedback_Or", "inC")
    builder.add_link("Chiller_D_Cmd", "out", "Feedback_Or", "inD")
    builder.add_link("Feedback_Or", "out", "Chiller_LeadLag", "feedback")

    # Wire timer
    builder.add_link("OneSecondTimer", "out", "TimerPulse", "in")

    # Wire logic for each chiller
    for chiller in chiller_names:
        # Wire lead/lag outputs to final commands
        builder.add_link(
            f"Chiller_LeadLag", f"out{chiller}", f"Chiller_{chiller}_Cmd", "in16"
        )

        # Enable counter only when the pulse fires AND the chiller is commanded on
        builder.add_link(
            "TimerPulse", "out", f"Chiller_{chiller}_RuntimeEnableGate", "inA"
        )
        builder.add_link(
            f"Chiller_{chiller}_Cmd",
            "out",
            f"Chiller_{chiller}_RuntimeEnableGate",
            "inB",
        )

        # When the gate is true, pass a '1' to the switch
        builder.add_link(
            f"Chiller_{chiller}_RuntimeEnableGate",
            "out",
            f"Chiller_{chiller}_PulseSwitch",
            "inSwitch",
        )
        builder.add_link("Const_1", "out", f"Chiller_{chiller}_PulseSwitch", "inTrue")

        # The switch output becomes the increment value for the counter
        builder.add_link(
            f"Chiller_{chiller}_PulseSwitch",
            "out",
            f"Chiller_{chiller}_RuntimeCounter",
            "countIncrement",
        )

        # The gate also triggers the 'countUp' slot to make the counter accumulate
        builder.add_link(
            f"Chiller_{chiller}_RuntimeEnableGate",
            "out",
            f"Chiller_{chiller}_RuntimeCounter",
            "countUp",
        )

        # Wire Counter output (seconds) back to LeadLagRuntime input (milliseconds) with conversion
        builder.add_link(
            f"Chiller_{chiller}_RuntimeCounter",
            "out",
            "Chiller_LeadLag",
            f"runtime{chiller}",
            link_type="b:ConversionLink",
            converter_type="conv:StatusNumericToRelTime",
        )

        # Wire the counter's output (accumulated seconds) directly for monitoring
        builder.add_link(
            f"Chiller_{chiller}_RuntimeCounter",
            "out",
            f"Chiller_{chiller}_Runtime_Out",
            "in16",
        )

    # --- Save the .bog file ---
    bog_filename = f"{script_filename}.bog"
    output_path = os.path.join(args.output_dir, bog_filename)
    os.makedirs(args.output_dir, exist_ok=True)
    builder.save(output_path)

    print(
        f"\nSuccessfully created Niagara .bog file at: {os.path.abspath(output_path)}"
    )
    print("Drag this file into Niagara Workbench to test the logic.")


if __name__ == "__main__":
    main()
