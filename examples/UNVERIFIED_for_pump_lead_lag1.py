import sys
import os
import argparse

from bog_builder import BogFolderBuilder


def main():
    parser = argparse.ArgumentParser(
        description="Build a .bog file for pump lead/lag logic with failure detection."
    )
    parser.add_argument(
        "-o", "--output_dir", default="examples", help="Output directory."
    )
    args = parser.parse_args()

    script_filename = os.path.basename(__file__).replace(".py", "")
    builder = BogFolderBuilder("PumpLeadLag")

    # --- Top-level Inputs ---
    # These represent the command issued to the pump and its actual running status.
    builder.add_boolean_writable(name="PumpA_Command", default_value=False)
    builder.add_boolean_writable(name="PumpA_Status", default_value=False)
    builder.add_boolean_writable(name="PumpB_Command", default_value=False)
    builder.add_boolean_writable(name="PumpB_Status", default_value=False)

    # User preference for which pump should be lead under normal conditions.
    # True = Pump A is preferred lead, False = Pump B is preferred lead.
    builder.add_boolean_writable(name="LeadPumpPreference_A", default_value=True)

    # Master enable for the entire lead/lag sequencing logic.
    builder.add_boolean_writable(name="LeadLag_Enable", default_value=True)

    # Delay in milliseconds for how long a command/status mismatch must persist
    # before a "failure" is confirmed. Note: For standard kitControl:BooleanDelay,
    # 'onDelay' is a static property set at creation, not a dynamically linkable slot.
    # This input will set the initial property value.
    builder.add_numeric_writable(
        name="FailureDetectionDelay_ms", default_value=5000.0, precision=0
    )

    # --- Top-level Outputs ---
    # Boolean point indicating if Pump A is currently designated as the lead pump.
    builder.add_boolean_writable(name="PumpA_IsLead", default_value=False)
    # Boolean point indicating if Pump B is currently designated as the lead pump.
    builder.add_boolean_writable(name="PumpB_IsLead", default_value=False)
    # The actual command sent to Pump A, controlled by the lead/lag logic.
    builder.add_boolean_writable(name="PumpA_OutputCmd", default_value=False)
    # The actual command sent to Pump B, controlled by the lead/lag logic.
    builder.add_boolean_writable(name="PumpB_OutputCmd", default_value=False)
    # Boolean point indicating if the currently active lead pump has a confirmed failure.
    builder.add_boolean_writable(name="LeadPumpFailureDetected", default_value=False)

    builder.start_sub_folder("PumpLeadLagLogic")

    # --- Mismatch Detection for each pump (Command XOR Status) ---
    builder.add_component(comp_type="kitControl:Xor", name="PumpA_Mismatch")
    builder.add_component(comp_type="kitControl:Xor", name="PumpB_Mismatch")

    # --- Delay for Confirmed Mismatch (BooleanDelay components) ---
    # The 'onDelay' property is set from the default value of 'FailureDetectionDelay_ms'.
    # This addresses the original error: 'onDelay' is a property, not a linkable slot.
    default_delay_ms_str = str(
        int(builder.get_component("FailureDetectionDelay_ms").properties["value"])
    )
    builder.add_component(
        comp_type="kitControl:BooleanDelay",
        name="PumpA_FailureDelay",
        properties={"onDelay": default_delay_ms_str, "offDelay": "0"},
    )
    builder.add_component(
        comp_type="kitControl:BooleanDelay",
        name="PumpB_FailureDelay",
        properties={"onDelay": default_delay_ms_str, "offDelay": "0"},
    )

    # --- Inverter Blocks for various logic conditions ---
    builder.add_component(
        comp_type="kitControl:Not", name="Not_LeadPumpPreference_A"
    )  # Gives true if B is preferred
    builder.add_component(
        comp_type="kitControl:Not", name="Not_PumpA_FailureDelay"
    )  # Gives true if Pump A is healthy
    builder.add_component(
        comp_type="kitControl:Not", name="Not_PumpB_FailureDelay"
    )  # Gives true if Pump B is healthy

    # --- Logic for determining if Pump A should be the lead ---
    # Condition 1: Pump A is preferred AND Pump A is healthy
    builder.add_component(comp_type="kitControl:And", name="And_A_Pref_And_A_Healthy")
    # Condition 2: Pump B is preferred AND Pump B has failed (so A takes over)
    builder.add_component(comp_type="kitControl:And", name="And_B_Pref_And_B_Failed")
    # Pump A is lead if (Condition 1 OR Condition 2)
    builder.add_component(comp_type="kitControl:Or", name="Or_PumpA_IsLead_Internal")

    # --- Logic for detecting if the CURRENTLY ACTIVE lead pump has a failure ---
    # Check if Pump A is lead AND Pump A has a confirmed failure
    builder.add_component(comp_type="kitControl:And", name="And_A_IsLead_And_A_Failed")
    # Check if Pump B is lead AND Pump B has a confirmed failure
    builder.add_component(comp_type="kitControl:And", name="And_B_IsLead_And_B_Failed")
    # Overall: Lead Pump Failure is detected if (And_A_IsLead_And_A_Failed OR And_B_IsLead_And_B_Failed)
    builder.add_component(comp_type="kitControl:Or", name="Or_OverallLeadFailure")

    # --- Logic for outputting actual pump commands ---
    builder.add_component(comp_type="kitControl:And", name="And_PumpA_OutCmd_Logic")
    builder.add_component(comp_type="kitControl:And", name="And_PumpB_OutCmd_Logic")

    builder.end_sub_folder()

    # --- Wiring Components ---

    # Mismatch Detection Wiring
    builder.add_link("PumpA_Command", "out", "PumpA_Mismatch", "inA")
    builder.add_link("PumpA_Status", "out", "PumpA_Mismatch", "inB")
    builder.add_link("PumpB_Command", "out", "PumpB_Mismatch", "inA")
    builder.add_link("PumpB_Status", "out", "PumpB_Mismatch", "inB")

    # Mismatch Delay Wiring
    builder.add_link("PumpA_Mismatch", "out", "PumpA_FailureDelay", "in")
    builder.add_link("PumpB_Mismatch", "out", "PumpB_FailureDelay", "in")

    # Inverter Wiring
    builder.add_link("LeadPumpPreference_A", "out", "Not_LeadPumpPreference_A", "in")
    builder.add_link("PumpA_FailureDelay", "out", "Not_PumpA_FailureDelay", "in")
    builder.add_link("PumpB_FailureDelay", "out", "Not_PumpB_FailureDelay", "in")

    # Lead Assignment Logic for Pump A
    builder.add_link("LeadPumpPreference_A", "out", "And_A_Pref_And_A_Healthy", "inA")
    builder.add_link("Not_PumpA_FailureDelay", "out", "And_A_Pref_And_A_Healthy", "inB")

    builder.add_link(
        "Not_LeadPumpPreference_A", "out", "And_B_Pref_And_B_Failed", "inA"
    )  # B is preferred
    builder.add_link(
        "PumpB_FailureDelay", "out", "And_B_Pref_And_B_Failed", "inB"
    )  # B has failed

    builder.add_link(
        "And_A_Pref_And_A_Healthy", "out", "Or_PumpA_IsLead_Internal", "inA"
    )
    builder.add_link(
        "And_B_Pref_And_B_Failed", "out", "Or_PumpA_IsLead_Internal", "inB"
    )
    builder.add_link("Or_PumpA_IsLead_Internal", "out", "PumpA_IsLead", "in16")

    # Lead Assignment Logic for Pump B (assuming a two-pump system, B is lead if A is not)
    builder.add_link(
        "Or_PumpA_IsLead_Internal",
        "out",
        "PumpB_IsLead",
        "in16",
        link_type="b:ConversionLink",
        converter_type="conv:BooleanToNotBoolean",
    )

    # Active Lead Pump Failure Detection Wiring
    builder.add_link("PumpA_IsLead", "out", "And_A_IsLead_And_A_Failed", "inA")
    builder.add_link("PumpA_FailureDelay", "out", "And_A_IsLead_And_A_Failed", "inB")

    builder.add_link("PumpB_IsLead", "out", "And_B_IsLead_And_B_Failed", "inA")
    builder.add_link("PumpB_FailureDelay", "out", "And_B_IsLead_And_B_Failed", "inB")

    builder.add_link("And_A_IsLead_And_A_Failed", "out", "Or_OverallLeadFailure", "inA")
    builder.add_link("And_B_IsLead_And_B_Failed", "out", "Or_OverallLeadFailure", "inB")
    builder.add_link("Or_OverallLeadFailure", "out", "LeadPumpFailureDetected", "in16")

    # Output Command Logic Wiring
    builder.add_link("PumpA_IsLead", "out", "And_PumpA_OutCmd_Logic", "inA")
    builder.add_link("LeadLag_Enable", "out", "And_PumpA_OutCmd_Logic", "inB")
    builder.add_link("And_PumpA_OutCmd_Logic", "out", "PumpA_OutputCmd", "in16")

    builder.add_link("PumpB_IsLead", "out", "And_PumpB_OutCmd_Logic", "inA")
    builder.add_link("LeadLag_Enable", "out", "And_PumpB_OutCmd_Logic", "inB")
    builder.add_link("And_PumpB_OutCmd_Logic", "out", "PumpB_OutputCmd", "in16")

    # --- Save the File ---
    bog_filename = f"pump_squencing.bog"
    output_path = os.path.join(args.output_dir, bog_filename)
    os.makedirs(args.output_dir, exist_ok=True)
    builder.save(output_path)
    print(f"\nSuccessfully created Niagara .bog file at: {output_path}")


if __name__ == "__main__":
    main()
