"""Additional functional tests for BogFolderBuilder using complex example scripts.

These tests replicate several more advanced Niagara Workbench examples provided
by the user (bool latch playground, finding the second highest value, manual
average/min/max logic, ping‑pong counter, periodic trigger loop, and selecting
the top five values from fifteen inputs).  They exercise the builder across a
wide variety of component types, link patterns and folder hierarchies.

Each test constructs the graph using the high‑level BogFolderBuilder API and
asserts that the resulting `.bog` file is created without raising any
validation exceptions.  The tests do not evaluate the functional behaviour
of the Niagara program itself; they simply ensure that the builder can
generate valid `.bog` archives for these use cases.
"""

from __future__ import annotations

import os
from pathlib import Path

from bog_builder import BogFolderBuilder


def test_bool_latch_playground(tmp_path: Path) -> None:
    """Replicate the BoolLatch playground example."""
    builder = BogFolderBuilder("BoolLatch_Playground", debug=False)
    # Top‑level knobs
    builder.add_numeric_writable("TOP", default_value=90.0, precision=2)
    builder.add_numeric_writable("BOTTOM", default_value=10.0, precision=2)
    builder.add_boolean_writable("CountDown", default_value=False)
    # Logic folder
    builder.start_sub_folder("LatchSandbox")
    builder.add_component("kitControl:SineWave", "SineWave")
    builder.add_component("kitControl:GreaterThanEqual", "GreaterThanEq")
    builder.add_component("kitControl:LessThanEqual", "LessThanEq")
    builder.add_component("kitControl:Or", "Or_Block")
    builder.add_component("kitControl:BooleanLatch", "BooleanLatch")
    builder.end_sub_folder()
    # Wiring
    builder.add_link("SineWave", "out", "GreaterThanEq", "inA")
    builder.add_link("SineWave", "out", "LessThanEq", "inA")
    builder.add_link("TOP", "out", "GreaterThanEq", "inB")
    builder.add_link("BOTTOM", "out", "LessThanEq", "inB")
    builder.add_link("GreaterThanEq", "out", "Or_Block", "inA")
    builder.add_link("LessThanEq", "out", "Or_Block", "inB")
    builder.add_link("GreaterThanEq", "out", "BooleanLatch", "clock")
    builder.add_link("Or_Block", "out", "BooleanLatch", "in")
    builder.add_link("BooleanLatch", "out", "CountDown", "in16")
    out_path = tmp_path / "bool_latch_playground.bog"
    builder.save(str(out_path))
    assert out_path.exists()


def _create_comparison_node(builder: BogFolderBuilder, input_a_name: str, input_b_name: str, node_id: str) -> tuple[str, str]:
    """Helper for building pairwise comparison logic: returns (max_switch, min_switch)."""
    gt_name = f"GT_{node_id}"
    max_switch_name = f"MaxSwitch_{node_id}"
    min_switch_name = f"MinSwitch_{node_id}"
    builder.add_component("kitControl:GreaterThan", gt_name)
    builder.add_numeric_switch(max_switch_name)
    builder.add_numeric_switch(min_switch_name)
    builder.add_link(input_a_name, "out", gt_name, "inA")
    builder.add_link(input_b_name, "out", gt_name, "inB")
    builder.add_link(gt_name, "out", max_switch_name, "inSwitch")
    builder.add_link(gt_name, "out", min_switch_name, "inSwitch")
    builder.add_link(input_a_name, "out", max_switch_name, "inTrue")
    builder.add_link(input_b_name, "out", max_switch_name, "inFalse")
    builder.add_link(input_b_name, "out", min_switch_name, "inTrue")
    builder.add_link(input_a_name, "out", min_switch_name, "inFalse")
    return max_switch_name, min_switch_name


def _create_combine_node(builder: BogFolderBuilder, max1_name: str, second1_name: str, max2_name: str, second2_name: str, node_id: str) -> tuple[str, str]:
    """Combine two (max, second) pairs into a single (max, second) pair."""
    overall_max, min_of_maxes = _create_comparison_node(builder, max1_name, max2_name, f"{node_id}_MaxCompare")
    intermediate_second, _ = _create_comparison_node(builder, min_of_maxes, second1_name, f"{node_id}_Second_A")
    overall_second, _ = _create_comparison_node(builder, intermediate_second, second2_name, f"{node_id}_Second_B")
    return overall_max, overall_second


def test_find_second_highest_of_6(tmp_path: Path) -> None:
    """Replicate the second highest of six example."""
    builder = BogFolderBuilder("FindTopTwoOfSixDampers")
    inputs = [f"VAV_Damper_{i}" for i in range(1, 7)]
    for i, name in enumerate(inputs):
        builder.add_numeric_writable(name, default_value=float(i * 10))
    builder.add_numeric_writable("HighestDamperPosition")
    builder.add_numeric_writable("SecondHighestDamperPosition")
    builder.start_sub_folder("CalculationLogic")
    tier1_results: list[tuple[str, str]] = []
    for i in range(3):
        input_a = inputs[i * 2]
        input_b = inputs[i * 2 + 1]
        tier1_results.append(_create_comparison_node(builder, input_a, input_b, f"T1_P{i}"))
    max1, second1 = tier1_results[0]
    max2, second2 = tier1_results[1]
    tier2_max, tier2_second = _create_combine_node(builder, max1, second1, max2, second2, "T2_C0")
    last_pair_max, last_pair_second = tier1_results[2]
    final_max, final_second = _create_combine_node(builder, tier2_max, tier2_second, last_pair_max, last_pair_second, "T3_C0")
    builder.end_sub_folder()
    builder.add_link(final_max, "out", "HighestDamperPosition", "in16")
    builder.add_link(final_second, "out", "SecondHighestDamperPosition", "in16")
    out_path = tmp_path / "find_second_highest_of_6.bog"
    builder.save(str(out_path))
    assert out_path.exists()


def test_hot_water_reset(tmp_path: Path) -> None:
    """Construct a hot water reset using the Reset block."""
    builder = BogFolderBuilder("HotWaterTempReset", debug=False)
    # Define numeric writables for outdoor temperature and limits
    builder.add_numeric_writable("OAT", default_value=11.0)
    builder.add_numeric_writable("OAT_LOW", default_value=0.0)
    builder.add_numeric_writable("OAT_HIGH", default_value=50.0)
    builder.add_numeric_writable("HWST_LOW", default_value=110.0)
    builder.add_numeric_writable("HWST_HIGH", default_value=160.0)
    # Define the Reset component with fallback values
    reset_props = {
        "inA": {"value": 11.0},
        "inputLowLimit": {"value": 0.0},
        "inputHighLimit": {"value": 50.0},
        "outputLowLimit": {"value": 160.0},
        "outputHighLimit": {"value": 110.0},
    }
    builder.add_component("kitControl:Reset", "Reset", properties=reset_props)
    builder.add_numeric_writable("HotWaterSupplyTempStp")
    # Wiring
    builder.add_link("OAT", "out", "Reset", "inA")
    builder.add_link("OAT_LOW", "out", "Reset", "inputLowLimit")
    builder.add_link("OAT_HIGH", "out", "Reset", "inputHighLimit")
    builder.add_link("HWST_HIGH", "out", "Reset", "outputLowLimit")
    builder.add_link("HWST_LOW", "out", "Reset", "outputHighLimit")
    builder.add_link("Reset", "out", "HotWaterSupplyTempStp", "in10")
    out_path = tmp_path / "hot_water_reset.bog"
    builder.save(str(out_path))
    assert out_path.exists()


def test_pid_loop(tmp_path: Path) -> None:
    """Construct a PID loop using a LoopPoint and conversion links."""
    builder = BogFolderBuilder("PID", debug=False)
    # Inputs and tuning writables
    builder.add_numeric_writable("Temp", default_value=80.0)
    builder.add_numeric_writable("Setpoint", default_value=70.0)
    builder.add_numeric_writable("PropBand", default_value=5.0)
    builder.add_numeric_writable("Integral", default_value=0.05)
    builder.add_boolean_writable("BooleanWritable", default_value=True)
    builder.add_boolean_writable("LoopActionDirect", default_value=False)
    # LoopPoint with fallback values for initial tuning
    lp_props = {
        "loopEnable": {"value": True},
        "controlledVariable": {"value": 80.0},
        "setpoint": {"value": 70.0},
        "proportionalConstant": {"value": 5.0},
        "integralConstant": {"value": 0.05},
    }
    builder.add_component("kitControl:LoopPoint", "LoopPoint", properties=lp_props)
    builder.add_numeric_writable("Output")
    # Wiring: process and setpoint
    builder.add_link("Temp", "out", "LoopPoint", "controlledVariable")
    builder.add_link("Setpoint", "out", "LoopPoint", "setpoint")
    # Conversion from LoopActionDirect to loopAction (boolean to enum)
    builder.add_link(
        "LoopActionDirect",
        "out",
        "LoopPoint",
        "loopAction",
        link_type="b:ConversionLink",
        converter_type="conv:StatusBooleanToFrozenEnum",
    )
    # Enable boolean: direct link
    builder.add_link("BooleanWritable", "out", "LoopPoint", "loopEnable")
    # Conversion from numeric writables to numeric constants (status numeric to number)
    builder.add_link(
        "PropBand",
        "out",
        "LoopPoint",
        "proportionalConstant",
        link_type="b:ConversionLink",
        converter_type="conv:StatusNumericToNumber",
    )
    builder.add_link(
        "Integral",
        "out",
        "LoopPoint",
        "integralConstant",
        link_type="b:ConversionLink",
        converter_type="conv:StatusNumericToNumber",
    )
    # Output wiring
    builder.add_link("LoopPoint", "out", "Output", "in10")
    out_path = tmp_path / "pid.bog"
    builder.save(str(out_path))
    assert out_path.exists()


def test_bool_schedule(tmp_path: Path) -> None:
    """
    Construct a simple Boolean schedule and verify that the builder writes
    a .bog file without errors.  Niagara requires the schedule palette
    to reference the ``schedule`` module (``sch=schedule``) rather than
    ``sch=sch``.  This test exercises the override in the builder that
    maps ``sch:BooleanSchedule`` to the correct module.
    """
    builder = BogFolderBuilder("Schedules_Bool", debug=False)
    # Define a Boolean schedule.  Provide an initial value for the out slot
    # to indicate the default state when no schedule events are active.
    builder.add_component(
        "sch:BooleanSchedule",
        "BooleanSchedule",
        properties={"out": {"value": True}},
    )
    # Define a Boolean writable that will consume the schedule output.
    builder.add_boolean_writable("BooleanWritable", default_value=False)
    # Wire the schedule's out to the writable's in16.  This should be a
    # straightforward data link.
    builder.add_link("BooleanSchedule", "out", "BooleanWritable", "in16")
    out_path = tmp_path / "bool_schedule.bog"
    builder.save(str(out_path))
    assert out_path.exists()


def test_numeric_schedule(tmp_path: Path) -> None:
    """
    Construct a simple Numeric schedule and verify that the builder writes a
    .bog file without errors.  Numeric schedules output a numeric value on
    their ``out`` slot and use ``defaultOutput`` to define the base value
    when the schedule is inactive.  This test ensures that the builder
    correctly maps schedule components to the ``schedule`` module and emits
    numeric status properties for ``defaultOutput`` and ``out``.
    """
    builder = BogFolderBuilder("Schedules_Numeric", debug=False)
    # Create a numeric schedule with a default value of 0 and an initial out value of 1.
    builder.add_component(
        "sch:NumericSchedule",
        "NumericSchedule",
        properties={
            "defaultOutput": {"value": 0.0},
            "out": {"value": 1.0},
        },
    )
    # A numeric writable to consume the schedule output.
    builder.add_numeric_writable("NumericWritable")
    builder.add_link("NumericSchedule", "out", "NumericWritable", "in16")
    out_path = tmp_path / "numeric_schedule.bog"
    builder.save(str(out_path))
    assert out_path.exists()


def test_enum_schedule(tmp_path: Path) -> None:
    """
    Construct a simple enumerated schedule and writable.  The schedule defines
    an enumeration with three duties and outputs one of them via its ``out``
    slot.  The EnumWritable declares the same facets mapping and will
    receive the schedule value on its ``in16`` input.  This test checks
    that the builder writes a valid .bog file and that the slot and
    component validation logic accommodates EnumSchedule and EnumWritable.
    """
    facets_map = "range=E:{duty1=1,duty2=2,duty3=3}"
    # Build the folder
    builder = BogFolderBuilder("Schedules_Enum", debug=False)
    # Enum schedule with facets and initial out value duty2 (i.e. 2@{...})
    builder.add_component(
        "sch:EnumSchedule",
        "EnumSchedule",
        properties={
            "facets": facets_map,
            "out": {"value": f"2@{{duty1=1,duty2=2,duty3=3}}"},
        },
    )
    # Enum writable with the same facets and default fallback value duty1 (1@...)
    builder.add_enum_writable("EnumWritable", facets=facets_map, default_value="1@{duty1=1,duty2=2,duty3=3}")
    # Wire the schedule to the writable
    builder.add_link("EnumSchedule", "out", "EnumWritable", "in16")
    out_path = tmp_path / "enum_schedule.bog"
    builder.save(str(out_path))
    assert out_path.exists()


def test_manual_average_min_max(tmp_path: Path) -> None:
    """Replicate the manual average/min/max example (similar to average_min_max)."""
    builder = BogFolderBuilder("MultiAlgorithmTestManual")
    # Inputs
    for i in range(1, 12):
        builder.add_numeric_writable(f"Input{i}", default_value=10.0 * i)
    # Outputs
    builder.add_numeric_writable("Min_Final")
    builder.add_numeric_writable("Max_Final")
    builder.add_numeric_writable("Avg_Final")
    # Subfolders and components
    builder.start_sub_folder("AverageLogic")
    for j in range(1, 5):
        builder.add_component("kitControl:Average", f"Avg{j}")
    builder.end_sub_folder()
    builder.start_sub_folder("MinimumLogic")
    for j in range(1, 5):
        builder.add_component("kitControl:Minimum", f"Min{j}")
    builder.end_sub_folder()
    builder.start_sub_folder("MaximumLogic")
    for j in range(1, 5):
        builder.add_component("kitControl:Maximum", f"Max{j}")
    builder.end_sub_folder()
    # Wiring for Average
    links_avg = [
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
    for src, tgt, slot in links_avg:
        builder.add_link(src, "out", tgt, slot)
    builder.add_link("Avg1", "out", "Avg4", "inA")
    builder.add_link("Avg2", "out", "Avg4", "inB")
    builder.add_link("Avg3", "out", "Avg4", "inC")
    builder.add_link("Avg4", "out", "Avg_Final", "in16")
    # Wiring for Min
    links_min = [
        ("Input1", "Min1", "inA"), ("Input2", "Min1", "inB"), ("Input3", "Min1", "inC"), ("Input4", "Min1", "inD"),
        ("Input5", "Min2", "inA"), ("Input6", "Min2", "inB"), ("Input7", "Min2", "inC"), ("Input8", "Min2", "inD"),
        ("Input9", "Min3", "inA"), ("Input10", "Min3", "inB"), ("Input11", "Min3", "inC"),
    ]
    for src, tgt, slot in links_min:
        builder.add_link(src, "out", tgt, slot)
    builder.add_link("Min1", "out", "Min4", "inA")
    builder.add_link("Min2", "out", "Min4", "inB")
    builder.add_link("Min3", "out", "Min4", "inC")
    builder.add_link("Min4", "out", "Min_Final", "in16")
    # Wiring for Max
    links_max = [
        ("Input1", "Max1", "inA"), ("Input2", "Max1", "inB"), ("Input3", "Max1", "inC"), ("Input4", "Max1", "inD"),
        ("Input5", "Max2", "inA"), ("Input6", "Max2", "inB"), ("Input7", "Max2", "inC"), ("Input8", "Max2", "inD"),
        ("Input9", "Max3", "inA"), ("Input10", "Max3", "inB"), ("Input11", "Max3", "inC"),
    ]
    for src, tgt, slot in links_max:
        builder.add_link(src, "out", tgt, slot)
    builder.add_link("Max1", "out", "Max4", "inA")
    builder.add_link("Max2", "out", "Max4", "inB")
    builder.add_link("Max3", "out", "Max4", "inC")
    builder.add_link("Max4", "out", "Max_Final", "in16")
    out_path = tmp_path / "manual_average_min_max.bog"
    builder.save(str(out_path))
    assert out_path.exists()


def test_ping_pong_counter(tmp_path: Path) -> None:
    """Replicate the ping‑pong counter example."""
    builder = BogFolderBuilder("PingPongCounter")
    builder.add_numeric_writable("CounterViewer", 0.0)
    builder.add_numeric_writable("Step", 1.0)
    builder.add_numeric_writable("TopLimit", 20.0)
    builder.add_numeric_writable("LowLimit", -20.0)
    builder.add_boolean_writable("ManualResetCounter", default_value=False)
    builder.start_sub_folder("Logic")
    builder.add_component("kitControl:MultiVibrator", "MultiViber", properties={"period": "2000"})
    builder.add_component("kitControl:Counter", "Counter")
    builder.add_component("kitControl:OneShot", "IncrementUpOneShot")
    builder.add_component("kitControl:OneShot", "IncrementDownOneShot")
    builder.add_component("kitControl:OneShot", "ResetOneShot")
    builder.add_component("kitControl:GreaterThanEqual", "AtOrAbove_TopLimit")
    builder.add_component("kitControl:LessThanEqual", "AtOrBelow_LowLimit")
    builder.add_component("kitControl:BooleanLatch", "IsCountingDown_Latch")
    builder.add_component("kitControl:Not", "IsNotCountingDown_Not")
    builder.add_component("kitControl:And", "UpPulse_Gate")
    builder.add_component("kitControl:And", "DownPulse_Gate")
    builder.end_sub_folder()
    # Wiring
    builder.add_link("Step", "out", "Counter", "countIncrement")
    builder.add_link("Counter", "out", "CounterViewer", "in16")
    builder.add_link("ManualResetCounter", "out", "ResetOneShot", "in")
    builder.add_link("ResetOneShot", "out", "Counter", "clear")
    builder.add_link("Counter", "out", "AtOrAbove_TopLimit", "inA")
    builder.add_link("TopLimit", "out", "AtOrAbove_TopLimit", "inB")
    builder.add_link("Counter", "out", "AtOrBelow_LowLimit", "inA")
    builder.add_link("LowLimit", "out", "AtOrBelow_LowLimit", "inB")
    builder.add_link("AtOrAbove_TopLimit", "out", "IsCountingDown_Latch", "set")
    builder.add_link("AtOrBelow_LowLimit", "out", "IsCountingDown_Latch", "reset")
    builder.add_link("IsCountingDown_Latch", "out", "IsNotCountingDown_Not", "in")
    builder.add_link("IsNotCountingDown_Not", "out", "UpPulse_Gate", "inA")
    builder.add_link("MultiViber", "out", "UpPulse_Gate", "inB")
    builder.add_link("UpPulse_Gate", "out", "IncrementUpOneShot", "in")
    builder.add_link("IncrementUpOneShot", "out", "Counter", "countUp")
    builder.add_link("IsCountingDown_Latch", "out", "DownPulse_Gate", "inA")
    builder.add_link("MultiViber", "out", "DownPulse_Gate", "inB")
    builder.add_link("DownPulse_Gate", "out", "IncrementDownOneShot", "in")
    builder.add_link("IncrementDownOneShot", "out", "Counter", "countDown")
    out_path = tmp_path / "ping_pong_counter.bog"
    builder.save(str(out_path))
    assert out_path.exists()


def test_test_periodic_trigger(tmp_path: Path) -> None:
    """Replicate the periodic trigger (DIY interval) example."""
    b = BogFolderBuilder("Test_Interval_DIY_ForLoop_Fixed")
    # Top level I/O
    b.add_boolean_writable("Enable", True)
    b.add_numeric_writable("Counter", 0.0)
    b.add_numeric_writable("Step", 5.0)
    b.add_numeric_writable("Target", 20.0)
    b.add_numeric_writable("Counter_Out", 0.0)
    # Interval subfolder
    b.start_sub_folder("Interval")
    b.add_component("kitControl:BooleanDelay", "TickDelay", properties={"onDelay": "5000"})
    b.add_component("kitControl:OneShot", "TickPulse")
    b.add_component("kitControl:Not", "PulseNot")
    b.add_component("kitControl:And", "Enable_AND_Hold")
    b.end_sub_folder()
    # Compare subfolder
    b.start_sub_folder("Compare")
    b.add_component("kitControl:GreaterThanEqual", "Reached_GE_Target")
    b.add_component("kitControl:Not", "NotReached")
    b.add_component("kitControl:And", "Enable_AND_NotReached")
    b.end_sub_folder()
    # Increment subfolder
    b.start_sub_folder("Increment")
    b.add_component("kitControl:Add", "CounterPlusStep")
    b.add_component("kitControl:NumericDelay", "UnitDelay", properties={"delayMs": "10"})
    b.add_numeric_switch("PulseGate")
    b.end_sub_folder()
    # Output stage
    b.start_sub_folder("OutputStage")
    b.add_numeric_switch("ReachedHold")
    b.end_sub_folder()
    # Wiring
    b.add_link("Counter", "out", "Reached_GE_Target", "inA")
    b.add_link("Target", "out", "Reached_GE_Target", "inB")
    b.add_link("Reached_GE_Target", "out", "NotReached", "in")
    b.add_link("Enable", "out", "Enable_AND_NotReached", "inA")
    b.add_link("NotReached", "out", "Enable_AND_NotReached", "inB")
    b.add_link("Enable_AND_NotReached", "out", "Enable_AND_Hold", "inA")
    b.add_link("PulseNot", "out", "Enable_AND_Hold", "inB")
    b.add_link("Enable_AND_Hold", "out", "TickDelay", "in")
    b.add_link("TickDelay", "out", "TickPulse", "in")
    b.add_link("TickPulse", "out", "PulseNot", "in")
    b.add_link("Counter", "out", "UnitDelay", "in")
    b.add_link("UnitDelay", "out", "CounterPlusStep", "inA")
    b.add_link("Step", "out", "CounterPlusStep", "inB")
    b.add_link("TickPulse", "out", "PulseGate", "inSwitch")
    b.add_link("CounterPlusStep", "out", "PulseGate", "inTrue")
    b.add_link("UnitDelay", "out", "PulseGate", "inFalse")
    b.add_link("PulseGate", "out", "Counter", "in16")
    b.add_link("Counter", "out", "Counter_Out", "in16")
    out_path = tmp_path / "test_periodic_trigger.bog"
    b.save(str(out_path))
    assert out_path.exists()


def _find_max_and_losers(builder: BogFolderBuilder, inputs: list[str], rank_label: str) -> tuple[str | None, list[str]]:
    """Tournament to find max value and collect losers."""
    if not inputs:
        return None, []
    if len(inputs) == 1:
        return inputs[0], []
    current_inputs = inputs[:]
    losers: list[str] = []
    round_num = 1
    while len(current_inputs) > 1:
        next_round: list[str] = []
        for i in range(0, len(current_inputs) - 1, 2):
            a = current_inputs[i]
            b = current_inputs[i + 1]
            max_node, min_node = _create_comparison_node(builder, a, b, f"{rank_label}_R{round_num}_P{i//2}")
            next_round.append(max_node)
            losers.append(min_node)
        if len(current_inputs) % 2 == 1:
            next_round.append(current_inputs[-1])
        current_inputs = next_round
        round_num += 1
    return current_inputs[0], losers


def test_top_five_of_fifteen(tmp_path: Path) -> None:
    """Replicate the top five of fifteen example."""
    builder = BogFolderBuilder("FindTop5Of15Dampers")
    inputs = [f"VAV_Damper_{i}" for i in range(1, 16)]
    for i, name in enumerate(inputs):
        builder.add_numeric_writable(name, default_value=float((i + 1) * 10))
    builder.add_numeric_writable("I_ignore_var", default_value=1.0)
    for rank in range(1, 6):
        builder.add_numeric_writable(f"Rank_{rank}_Highest")
    builder.add_numeric_writable("Filtered_Max")
    remaining_candidates = inputs[:]
    top_5_winners: list[str] = []
    for rank in range(1, 6):
        if not remaining_candidates:
            break
        builder.start_sub_folder(f"Rank_{rank}")
        winner, losers = _find_max_and_losers(builder, remaining_candidates, f"Rank{rank}")
        builder.end_sub_folder()
        if winner:
            top_5_winners.append(winner)
            builder.add_link(winner, "out", f"Rank_{rank}_Highest", "in16")
        remaining_candidates = losers
    builder.start_sub_folder("SelectionLogic")
    builder.add_numeric_select("Ignore")
    builder.end_sub_folder()
    if top_5_winners:
        for i, winner_name in enumerate(top_5_winners):
            target_slot = f"in{chr(65 + i)}"
            builder.add_link(winner_name, "out", "Ignore", target_slot)
        builder.add_link("I_ignore_var", "out", "Ignore", "select")
        builder.add_link("Ignore", "out", "Filtered_Max", "in16")
    out_path = tmp_path / "top_five_of_fifteen.bog"
    builder.save(str(out_path))
    assert out_path.exists()