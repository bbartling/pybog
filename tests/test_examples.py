"""Functional tests for the BogFolderBuilder.

Each test replicates one of the example scripts provided in the original project.
The goal is to ensure that no exceptions are raised during construction and that
the resulting `.bog` file is created successfully in a temporary directory.
"""

import os
from pathlib import Path

from bog_builder import BogFolderBuilder


def test_addition_complicated(tmp_path: Path) -> None:
    builder = BogFolderBuilder("ComplicatedAdder")
    # Inputs
    for i in range(1, 9 + 1):
        builder.add_numeric_writable(f"Input{i}", default_value=10.0 * i)
    # Output
    builder.add_numeric_writable("Total")
    builder.start_sub_folder("AdditionLogic")
    # Use the dedicated helper methods instead of the generic add_component
    builder.add_add("Add1")
    builder.add_add("Add2")
    builder.add_add("Add3")
    builder.end_sub_folder()
    # Wiring
    builder.add_link("Input1", "out", "Add1", "inA")
    builder.add_link("Input2", "out", "Add1", "inB")
    builder.add_link("Input3", "out", "Add1", "inC")
    builder.add_link("Input4", "out", "Add1", "inD")
    builder.add_link("Input5", "out", "Add2", "inA")
    builder.add_link("Input6", "out", "Add2", "inB")
    builder.add_link("Input7", "out", "Add2", "inC")
    builder.add_link("Input8", "out", "Add2", "inD")
    builder.add_link("Add1", "out", "Add3", "inA")
    builder.add_link("Add2", "out", "Add3", "inB")
    builder.add_link("Add3", "out", "Total", "in16")
    out_path = tmp_path / "addition_complicated.bog"
    builder.save(str(out_path))
    assert out_path.exists()


def test_average_min_max(tmp_path: Path) -> None:
    builder = BogFolderBuilder("MultiAlgorithmTest")
    # Inputs
    for i in range(1, 12):
        builder.add_numeric_writable(f"Input{i}", default_value=10.0 * i)
    # Outputs
    builder.add_numeric_writable("Min_Final")
    builder.add_numeric_writable("Max_Final")
    builder.add_numeric_writable("Avg_Final")
    # Average Logic
    builder.start_sub_folder("AverageLogic")
    for j in range(1, 5):
        # Average blocks should be created via the helper
        builder.add_average(f"Avg{j}")
    builder.end_sub_folder()
    # Minimum Logic
    builder.start_sub_folder("MinimumLogic")
    for j in range(1, 5):
        builder.add_minimum(f"Min{j}")
    builder.end_sub_folder()
    # Maximum Logic
    builder.start_sub_folder("MaximumLogic")
    for j in range(1, 5):
        builder.add_maximum(f"Max{j}")
    builder.end_sub_folder()
    # Wiring for Average
    links = [
        ("Input1", "Avg1", "inA"),
        ("Input2", "Avg1", "inB"),
        ("Input3", "Avg1", "inC"),
        ("Input4", "Avg1", "inD"),
        ("Input5", "Avg2", "inA"),
        ("Input6", "Avg2", "inB"),
        ("Input7", "Avg2", "inC"),
        ("Input8", "Avg2", "inD"),
        ("Input9", "Avg3", "inA"),
        ("Input10", "Avg3", "inB"),
        ("Input11", "Avg3", "inC"),
    ]
    for src, tgt, slot in links:
        builder.add_link(src, "out", tgt, slot)
    builder.add_link("Avg1", "out", "Avg4", "inA")
    builder.add_link("Avg2", "out", "Avg4", "inB")
    builder.add_link("Avg3", "out", "Avg4", "inC")
    builder.add_link("Avg4", "out", "Avg_Final", "in16")
    # Wiring for Minimum
    links_min = [
        ("Input1", "Min1", "inA"),
        ("Input2", "Min1", "inB"),
        ("Input3", "Min1", "inC"),
        ("Input4", "Min1", "inD"),
        ("Input5", "Min2", "inA"),
        ("Input6", "Min2", "inB"),
        ("Input7", "Min2", "inC"),
        ("Input8", "Min2", "inD"),
        ("Input9", "Min3", "inA"),
        ("Input10", "Min3", "inB"),
        ("Input11", "Min3", "inC"),
    ]
    for src, tgt, slot in links_min:
        builder.add_link(src, "out", tgt, slot)
    builder.add_link("Min1", "out", "Min4", "inA")
    builder.add_link("Min2", "out", "Min4", "inB")
    builder.add_link("Min3", "out", "Min4", "inC")
    builder.add_link("Min4", "out", "Min_Final", "in16")
    # Wiring for Maximum
    links_max = [
        ("Input1", "Max1", "inA"),
        ("Input2", "Max1", "inB"),
        ("Input3", "Max1", "inC"),
        ("Input4", "Max1", "inD"),
        ("Input5", "Max2", "inA"),
        ("Input6", "Max2", "inB"),
        ("Input7", "Max2", "inC"),
        ("Input8", "Max2", "inD"),
        ("Input9", "Max3", "inA"),
        ("Input10", "Max3", "inB"),
        ("Input11", "Max3", "inC"),
    ]
    for src, tgt, slot in links_max:
        builder.add_link(src, "out", tgt, slot)
    builder.add_link("Max1", "out", "Max4", "inA")
    builder.add_link("Max2", "out", "Max4", "inB")
    builder.add_link("Max3", "out", "Max4", "inC")
    builder.add_link("Max4", "out", "Max_Final", "in16")
    out_path = tmp_path / "average_min_max.bog"
    builder.save(str(out_path))
    assert out_path.exists()


def test_bool_logic_playground(tmp_path: Path) -> None:
    builder = BogFolderBuilder("BoolLogic_Playground", debug=False)
    # Inputs
    builder.add_boolean_writable("Bool_A", default_value=True)
    builder.add_boolean_writable("Bool_B", default_value=False)
    builder.add_numeric_writable("Num_A", default_value=5.0)
    builder.add_numeric_writable("Num_B", default_value=10.0)
    # Outputs
    outputs = [
        "Bool_Output_And",
        "Bool_Output_Or",
        "Bool_Output_Xor",
        "Bool_Output_Not",
        "Bool_Output_Equal",
        "Bool_Output_NotEqual",
        "Bool_Output_GT",
        "Bool_Output_GTE",
        "Bool_Output_LT",
        "Bool_Output_LTE",
    ]
    for o in outputs:
        builder.add_boolean_writable(o)
    # Subfolders
    builder.start_sub_folder("BooleanLogic")
    builder.add_and("And_Block")
    builder.add_or("Or_Block")
    builder.add_xor("Xor_Block")
    builder.add_not("Not_Block")
    builder.end_sub_folder()
    builder.start_sub_folder("ComparisonLogic")
    builder.add_equal("Equal_Block")
    builder.add_not_equal("NotEqual_Block")
    builder.add_greater_than("GreaterThan_Block")
    builder.add_greater_than_equal("GreaterThanEqual_Block")
    builder.add_less_than("LessThan_Block")
    builder.add_less_than_equal("LessThanEqual_Block")
    builder.end_sub_folder()
    # Wiring Boolean logic
    builder.add_link("Bool_A", "out", "And_Block", "inA")
    builder.add_link("Bool_B", "out", "And_Block", "inB")
    builder.add_link("And_Block", "out", "Bool_Output_And", "in16")
    builder.add_link("Bool_A", "out", "Or_Block", "inA")
    builder.add_link("Bool_B", "out", "Or_Block", "inB")
    builder.add_link("Or_Block", "out", "Bool_Output_Or", "in16")
    builder.add_link("Bool_A", "out", "Xor_Block", "inA")
    builder.add_link("Bool_B", "out", "Xor_Block", "inB")
    builder.add_link("Xor_Block", "out", "Bool_Output_Xor", "in16")
    builder.add_link("Bool_B", "out", "Not_Block", "in")
    builder.add_link("Not_Block", "out", "Bool_Output_Not", "in16")
    # Wiring Comparisons
    builder.add_link("Num_A", "out", "Equal_Block", "inA")
    builder.add_link("Num_B", "out", "Equal_Block", "inB")
    builder.add_link("Equal_Block", "out", "Bool_Output_Equal", "in16")
    builder.add_link("Num_A", "out", "NotEqual_Block", "inA")
    builder.add_link("Num_B", "out", "NotEqual_Block", "inB")
    builder.add_link("NotEqual_Block", "out", "Bool_Output_NotEqual", "in16")
    builder.add_link("Num_A", "out", "GreaterThan_Block", "inA")
    builder.add_link("Num_B", "out", "GreaterThan_Block", "inB")
    builder.add_link("GreaterThan_Block", "out", "Bool_Output_GT", "in16")
    builder.add_link("Num_A", "out", "GreaterThanEqual_Block", "inA")
    builder.add_link("Num_B", "out", "GreaterThanEqual_Block", "inB")
    builder.add_link("GreaterThanEqual_Block", "out", "Bool_Output_GTE", "in16")
    builder.add_link("Num_A", "out", "LessThan_Block", "inA")
    builder.add_link("Num_B", "out", "LessThan_Block", "inB")
    builder.add_link("LessThan_Block", "out", "Bool_Output_LT", "in16")
    builder.add_link("Num_A", "out", "LessThanEqual_Block", "inA")
    builder.add_link("Num_B", "out", "LessThanEqual_Block", "inB")
    builder.add_link("LessThanEqual_Block", "out", "Bool_Output_LTE", "in16")
    out_path = tmp_path / "bool_logic_playground.bog"
    builder.save(str(out_path))
    assert out_path.exists()


def test_boolean_numeric_switch(tmp_path: Path) -> None:
    builder = BogFolderBuilder("BooleanLogicNumericSwitch", debug=False)
    builder.add_numeric_writable("Input_A", default_value=100.0)
    builder.add_numeric_writable("Input_B", default_value=40.0)
    builder.add_boolean_writable("BooleanWritable", default_value=False)
    builder.add_numeric_writable("Output")
    builder.start_sub_folder("CalculationLogic")
    builder.add_add("Add")
    builder.add_subtract("Subtract")
    builder.add_equal("Equal")
    builder.add_numeric_switch("NumericSwitch")
    builder.add_numeric_writable("Const_True", default_value=1.0)
    builder.end_sub_folder()
    builder.add_link("Input_A", "out", "Add", "inA")
    builder.add_link("Input_B", "out", "Add", "inB")
    builder.add_link("Input_A", "out", "Subtract", "inA")
    builder.add_link("Input_B", "out", "Subtract", "inB")
    builder.add_link("BooleanWritable", "out", "Equal", "inA")
    builder.add_link("Const_True", "out", "Equal", "inB")
    builder.add_link("Equal", "out", "NumericSwitch", "inSwitch")
    builder.add_link("Add", "out", "NumericSwitch", "inTrue")
    builder.add_link("Subtract", "out", "NumericSwitch", "inFalse")
    builder.add_link("NumericSwitch", "out", "Output", "in16")
    out_path = tmp_path / "boolean_numeric_switch.bog"
    builder.save(str(out_path))
    assert out_path.exists()


def test_find_max_value(tmp_path: Path) -> None:
    builder = BogFolderBuilder("FindMaxValueWithSwitches")
    inputs = [f"VAV_{i}" for i in range(1, 11)]
    for name in inputs:
        # use numeric part of name for default_value
        builder.add_numeric_writable(name, default_value=float(name.split("_")[1]))
    builder.add_numeric_writable("MaxValue")
    builder.start_sub_folder("CalculationLogic")
    current_tier_outputs = inputs[:]
    tier_num = 1
    while len(current_tier_outputs) > 1:
        next_tier_outputs: list[str] = []
        for i in range(len(current_tier_outputs) // 2):
            input_a = current_tier_outputs[i * 2]
            input_b = current_tier_outputs[i * 2 + 1]
            pair_id = f"T{tier_num}_P{i}"
            gt_name = f"GT_{pair_id}"
            switch_name = f"Switch_{pair_id}"
            builder.add_greater_than(gt_name)
            builder.add_numeric_switch(switch_name)
            builder.add_link(input_a, "out", gt_name, "inA")
            builder.add_link(input_b, "out", gt_name, "inB")
            builder.add_link(gt_name, "out", switch_name, "inSwitch")
            builder.add_link(input_a, "out", switch_name, "inTrue")
            builder.add_link(input_b, "out", switch_name, "inFalse")
            next_tier_outputs.append(switch_name)
        if len(current_tier_outputs) % 2 == 1:
            passthrough = current_tier_outputs[-1]
            next_tier_outputs.append(passthrough)
        current_tier_outputs = next_tier_outputs
        tier_num += 1
    final_winner = current_tier_outputs[0]
    builder.end_sub_folder()
    builder.add_link(final_winner, "out", "MaxValue", "in16")
    out_path = tmp_path / "find_max_value.bog"
    builder.save(str(out_path))
    assert out_path.exists()


def test_minimal_latch_demo(tmp_path: Path) -> None:
    builder = BogFolderBuilder("Minimal_Latch_Demo", debug=False)
    builder.add_boolean_writable("Input_Signal", default_value=False)
    builder.add_boolean_writable("Clock_Signal", default_value=False)
    builder.add_boolean_latch("My_Latch")
    builder.add_boolean_writable("Latched_Output", default_value=False)
    builder.add_link("Input_Signal", "out", "My_Latch", "in")
    builder.add_link("Clock_Signal", "out", "My_Latch", "clock")
    builder.add_link("My_Latch", "out", "Latched_Output", "in16")
    out_path = tmp_path / "minimal_latch_demo.bog"
    builder.save(str(out_path))
    assert out_path.exists()


def test_numeric_select(tmp_path: Path) -> None:
    builder = BogFolderBuilder("NumericSelectTest")
    builder.start_sub_folder("CalculationLogic")
    # Inputs
    values = {
        "Input_A": 100.0,
        "Input_B": 200.0,
        "Input_C": 300.0,
        "Input_D": 400.0,
        "Input_E": 500.0,
    }
    for name, val in values.items():
        builder.add_numeric_writable(name, default_value=val)
    builder.add_numeric_writable("Selector", default_value=1.0)
    builder.add_numeric_select("MySelect")
    builder.add_numeric_writable("Selected_Value")
    builder.end_sub_folder()
    # Wiring
    slots = ["inA", "inB", "inC", "inD", "inE"]
    for (name, _), slot in zip(values.items(), slots):
        builder.add_link(name, "out", "MySelect", slot)
    builder.add_link("Selector", "out", "MySelect", "select")
    builder.add_link("MySelect", "out", "Selected_Value", "in16")
    out_path = tmp_path / "numeric_select.bog"
    builder.save(str(out_path))
    assert out_path.exists()


def test_numeric_switch_test(tmp_path: Path) -> None:
    builder = BogFolderBuilder("NumericSwitch_Isolation_Test")
    builder.add_boolean_writable("Switch_Control", default_value=True)
    builder.add_numeric_writable("Final_Output")
    builder.start_sub_folder("CalculationLogic")
    builder.add_numeric_const("Const_1", properties={"out": 1.0})
    builder.add_numeric_switch("Test_NumericSwitch")
    builder.end_sub_folder()
    builder.add_link("Switch_Control", "out", "Test_NumericSwitch", "inSwitch")
    builder.add_link("Const_1", "out", "Test_NumericSwitch", "inTrue")
    builder.add_link("Test_NumericSwitch", "out", "Final_Output", "in16")
    out_path = tmp_path / "numeric_switch_test.bog"
    builder.save(str(out_path))
    assert out_path.exists()


def test_one_shot_bool_delay_test(tmp_path: Path) -> None:
    builder = BogFolderBuilder("PulseDelayTest")
    builder.add_boolean_writable("Trigger", default_value=False)
    builder.add_boolean_writable("Output", default_value=False)
    builder.start_sub_folder("PulseDelay")
    builder.add_one_shot("OneShot1")
    # BooleanDelay uses the dedicated helper; passing the delay values via properties preserves behaviour
    builder.add_boolean_delay(
        "BooleanDelay",
        properties={"onDelay": "2000", "offDelay": "0"},
    )
    builder.end_sub_folder()
    builder.add_link("Trigger", "out", "OneShot1", "in")
    builder.add_link("OneShot1", "out", "BooleanDelay", "in")
    builder.add_link("BooleanDelay", "out", "Output", "in16")
    out_path = tmp_path / "one_shot_bool_delay_test.bog"
    builder.save(str(out_path))
    assert out_path.exists()
