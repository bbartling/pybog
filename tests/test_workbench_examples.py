"""Extra workbench example tests for BogFolderBuilder.

These tests mirror the standalone scripts provided alongside this project
(``bool_latch_play_ground.py``, ``find_second_highest_of_6.py``,
``manual_average_min_max.py``, ``ping_pong_counter.py``,
``test_periodic_trigger.py`` and ``top_five_of_fifteen.py``).  Each test
constructs the Niagara graph described by its corresponding script using the
``BogFolderBuilder`` API, then saves the resulting `.bog` file to a
temporary directory.  The existence of the file indicates that all
validations passed and the builder successfully constructed the archive.

These tests are intentionally redundant with those in ``test_more_examples.py``
but follow the naming and organisational structure found in the original
Workbench examples exactly.  Having both sets of tests helps ensure that
refactorings do not inadvertently diverge from the reference scripts.
"""

from __future__ import annotations

import os
from pathlib import Path

from bog_builder import BogFolderBuilder


def test_workbench_bool_latch_play_ground(tmp_path: Path) -> None:
    """Recreate the BoolLatchPlayGround script using the builder."""
    # The workbench script names its root folder "BoolLatch_Playground"
    builder = BogFolderBuilder("BoolLatch_Playground", debug=False)
    # Top‑level controls
    builder.add_numeric_writable("TOP", default_value=90.0, precision=2)
    builder.add_numeric_writable("BOTTOM", default_value=10.0, precision=2)
    builder.add_boolean_writable("CountDown", default_value=False)
    # Logic sub‑folder
    builder.start_sub_folder("LatchSandbox")
    builder.add_sine_wave("SineWave")
    builder.add_greater_than_equal("GreaterThanEq")
    builder.add_less_than_equal("LessThanEq")
    builder.add_or("Or_Block")
    builder.add_boolean_latch("BooleanLatch")
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
    # Save and verify
    out_path = tmp_path / "bool_latch_play_ground.bog"
    builder.save(str(out_path))
    assert out_path.exists()


def _compare_pair(
    builder: BogFolderBuilder, a: str, b: str, node_id: str
) -> tuple[str, str]:
    """Helper to construct GreaterThan + two NumericSwitch blocks like the find_second example."""
    gt = f"GT_{node_id}"
    max_sw = f"MaxSwitch_{node_id}"
    min_sw = f"MinSwitch_{node_id}"
    builder.add_greater_than(gt)
    builder.add_numeric_switch(max_sw)
    builder.add_numeric_switch(min_sw)
    builder.add_link(a, "out", gt, "inA")
    builder.add_link(b, "out", gt, "inB")
    builder.add_link(gt, "out", max_sw, "inSwitch")
    builder.add_link(gt, "out", min_sw, "inSwitch")
    builder.add_link(a, "out", max_sw, "inTrue")
    builder.add_link(b, "out", max_sw, "inFalse")
    builder.add_link(b, "out", min_sw, "inTrue")
    builder.add_link(a, "out", min_sw, "inFalse")
    return max_sw, min_sw


def test_workbench_find_second_highest_of_6(tmp_path: Path) -> None:
    """Recreate the find_second_highest_of_6 example script."""
    builder = BogFolderBuilder("FindTopTwoOfSixDampers")
    inputs = [f"VAV_Damper_{i}" for i in range(1, 7)]
    for i, name in enumerate(inputs):
        builder.add_numeric_writable(name, default_value=float(i * 10))
    builder.add_numeric_writable("HighestDamperPosition")
    builder.add_numeric_writable("SecondHighestDamperPosition")
    builder.start_sub_folder("CalculationLogic")
    # Tier 1: pairwise comparisons
    tier1: list[tuple[str, str]] = []
    for i in range(3):
        a = inputs[i * 2]
        b = inputs[i * 2 + 1]
        tier1.append(_compare_pair(builder, a, b, f"T1_P{i}"))
    # Tier 2: combine two pairs
    max1, second1 = tier1[0]
    max2, second2 = tier1[1]
    # Compare max1 vs max2 and then compute second1/second2 logic
    t2_max, min_of_maxes = _compare_pair(builder, max1, max2, "T2_C0_MaxCompare")
    inter_second, _ = _compare_pair(builder, min_of_maxes, second1, "T2_C0_Second_A")
    t2_second, _ = _compare_pair(builder, inter_second, second2, "T2_C0_Second_B")
    # Tier 3: combine with last pair
    last_max, last_second = tier1[2]
    final_max, min_of_t3_maxes = _compare_pair(
        builder, t2_max, last_max, "T3_C0_MaxCompare"
    )
    inter_second2, _ = _compare_pair(
        builder, min_of_t3_maxes, t2_second, "T3_C0_Second_A"
    )
    final_second, _ = _compare_pair(
        builder, inter_second2, last_second, "T3_C0_Second_B"
    )
    builder.end_sub_folder()
    builder.add_link(final_max, "out", "HighestDamperPosition", "in16")
    builder.add_link(final_second, "out", "SecondHighestDamperPosition", "in16")
    out_path = tmp_path / "find_second_highest_of_6.bog"
    builder.save(str(out_path))
    assert out_path.exists()


def test_workbench_manual_average_min_max(tmp_path: Path) -> None:
    """Recreate the manual_average_min_max script."""
    builder = BogFolderBuilder("MultiAlgorithmTest")
    # Inputs
    for i in range(1, 12):
        builder.add_numeric_writable(f"Input{i}", default_value=float(i * 10))
    # Outputs
    builder.add_numeric_writable("Min_Final")
    builder.add_numeric_writable("Max_Final")
    builder.add_numeric_writable("Avg_Final")
    # Average subfolder
    builder.start_sub_folder("AverageLogic")
    builder.add_average("Avg1")
    builder.add_average("Avg2")
    builder.add_average("Avg3")
    builder.add_average("Avg4")
    builder.end_sub_folder()
    # Minimum subfolder
    builder.start_sub_folder("MinimumLogic")
    builder.add_minimum("Min1")
    builder.add_minimum("Min2")
    builder.add_minimum("Min3")
    builder.add_minimum("Min4")
    builder.end_sub_folder()
    # Maximum subfolder
    builder.start_sub_folder("MaximumLogic")
    builder.add_maximum("Max1")
    builder.add_maximum("Max2")
    builder.add_maximum("Max3")
    builder.add_maximum("Max4")
    builder.end_sub_folder()
    # Average wiring
    builder.add_link("Input1", "out", "Avg1", "inA")
    builder.add_link("Input2", "out", "Avg1", "inB")
    builder.add_link("Input3", "out", "Avg1", "inC")
    builder.add_link("Input4", "out", "Avg1", "inD")
    builder.add_link("Input5", "out", "Avg2", "inA")
    builder.add_link("Input6", "out", "Avg2", "inB")
    builder.add_link("Input7", "out", "Avg2", "inC")
    builder.add_link("Input8", "out", "Avg2", "inD")
    builder.add_link("Input9", "out", "Avg3", "inA")
    builder.add_link("Input10", "out", "Avg3", "inB")
    builder.add_link("Input11", "out", "Avg3", "inC")
    builder.add_link("Avg1", "out", "Avg4", "inA")
    builder.add_link("Avg2", "out", "Avg4", "inB")
    builder.add_link("Avg3", "out", "Avg4", "inC")
    builder.add_link("Avg4", "out", "Avg_Final", "in16")
    # Minimum wiring
    builder.add_link("Input1", "out", "Min1", "inA")
    builder.add_link("Input2", "out", "Min1", "inB")
    builder.add_link("Input3", "out", "Min1", "inC")
    builder.add_link("Input4", "out", "Min1", "inD")
    builder.add_link("Input5", "out", "Min2", "inA")
    builder.add_link("Input6", "out", "Min2", "inB")
    builder.add_link("Input7", "out", "Min2", "inC")
    builder.add_link("Input8", "out", "Min2", "inD")
    builder.add_link("Input9", "out", "Min3", "inA")
    builder.add_link("Input10", "out", "Min3", "inB")
    builder.add_link("Input11", "out", "Min3", "inC")
    builder.add_link("Min1", "out", "Min4", "inA")
    builder.add_link("Min2", "out", "Min4", "inB")
    builder.add_link("Min3", "out", "Min4", "inC")
    builder.add_link("Min4", "out", "Min_Final", "in16")
    # Maximum wiring
    builder.add_link("Input1", "out", "Max1", "inA")
    builder.add_link("Input2", "out", "Max1", "inB")
    builder.add_link("Input3", "out", "Max1", "inC")
    builder.add_link("Input4", "out", "Max1", "inD")
    builder.add_link("Input5", "out", "Max2", "inA")
    builder.add_link("Input6", "out", "Max2", "inB")
    builder.add_link("Input7", "out", "Max2", "inC")
    builder.add_link("Input8", "out", "Max2", "inD")
    builder.add_link("Input9", "out", "Max3", "inA")
    builder.add_link("Input10", "out", "Max3", "inB")
    builder.add_link("Input11", "out", "Max3", "inC")
    builder.add_link("Max1", "out", "Max4", "inA")
    builder.add_link("Max2", "out", "Max4", "inB")
    builder.add_link("Max3", "out", "Max4", "inC")
    builder.add_link("Max4", "out", "Max_Final", "in16")
    out_path = tmp_path / "manual_average_min_max.bog"
    builder.save(str(out_path))
    assert out_path.exists()


def test_workbench_ping_pong_counter(tmp_path: Path) -> None:
    """Recreate the ping_pong_counter script exactly."""
    script_name = "PingPongCounter"
    # Create the builder with the provided name
    b = BogFolderBuilder(script_name)

    # ---- Top-level I/O (same labels as your sheet) ----
    b.add_boolean_writable("ManualReset", default_value=False)
    b.add_boolean_writable("Enabled", default_value=True)
    b.add_numeric_writable("Step", default_value=1.05)
    b.add_numeric_writable("TopLimit", default_value=20.0)
    b.add_numeric_writable("LowLimit", default_value=-20.0)
    b.add_numeric_writable("Output")

    # ---- Logic subfolder ----
    b.start_sub_folder("Logic")
    b.add_multi_vibrator("MultiVibrator", period_ms="2000")
    b.add_one_shot("FireOneShot")
    b.add_and("And")
    b.add_counter("Counter")
    b.add_greater_than_equal("GreaterThanEq")
    b.add_less_than_equal("LessThanEq")
    b.add_or("Or1")
    b.add_boolean_latch("BooleanLatch")
    b.add_boolean_switch("CountDown")
    b.add_boolean_switch("CountUp")
    b.add_one_shot("ResetOneShot")

    b.end_sub_folder()

    # ---- Wiring (inside Logic) ----
    b.add_link("MultiVibrator", "out", "FireOneShot", "in")
    b.add_link("FireOneShot", "out", "And", "inA")
    b.add_link("Enabled", "out", "And", "inB")
    b.add_link("Step", "out", "Counter", "countIncrement")
    b.add_link("ManualReset", "out", "ResetOneShot", "in")
    b.add_link("ResetOneShot", "out", "Counter", "clear")
    b.add_link("Counter", "out", "Output", "in16")
    b.add_link("Counter", "out", "GreaterThanEq", "inA")
    b.add_link("TopLimit", "out", "GreaterThanEq", "inB")
    b.add_link("Counter", "out", "LessThanEq", "inA")
    b.add_link("LowLimit", "out", "LessThanEq", "inB")
    b.add_link("GreaterThanEq", "out", "Or1", "inA")
    b.add_link("LessThanEq", "out", "Or1", "inB")
    b.add_link("Or1", "out", "BooleanLatch", "clock")
    b.add_link("GreaterThanEq", "out", "BooleanLatch", "in")
    b.add_link("BooleanLatch", "out", "CountDown", "inSwitch")
    b.add_link("BooleanLatch", "out", "CountUp", "inSwitch")
    b.add_link("And", "out", "CountDown", "inTrue")
    b.add_link("And", "out", "CountUp", "inFalse")
    b.add_link("CountDown", "out", "Counter", "countDown")
    b.add_link("CountUp", "out", "Counter", "countUp")

    # Save
    out_path = tmp_path / "ping_pong_counter.bog"
    b.save(str(out_path))
    assert out_path.exists()


def test_workbench_test_periodic_trigger(tmp_path: Path) -> None:
    """Recreate the test_periodic_trigger example exactly."""
    builder = BogFolderBuilder("Test_Interval_DIY_ForLoop_Fixed")
    # Top level I/O
    builder.add_boolean_writable("Enable", True)
    builder.add_numeric_writable("Counter", 0.0)
    builder.add_numeric_writable("Step", 5.0)
    builder.add_numeric_writable("Target", 20.0)
    builder.add_numeric_writable("Counter_Out", 0.0)
    # Interval
    builder.start_sub_folder("Interval")
    builder.add_boolean_delay("TickDelay", on_delay="5000")
    builder.add_one_shot("TickPulse")
    builder.add_not("PulseNot")
    builder.add_and("Enable_AND_Hold")
    builder.end_sub_folder()
    # Compare
    builder.start_sub_folder("Compare")
    builder.add_greater_than_equal("Reached_GE_Target")
    builder.add_not("NotReached")
    builder.add_and("Enable_AND_NotReached")
    builder.end_sub_folder()
    # Increment
    builder.start_sub_folder("Increment")
    builder.add_add("CounterPlusStep")
    builder.add_numeric_delay("UnitDelay", update_time="10")
    builder.add_numeric_switch("PulseGate")
    builder.end_sub_folder()
    # Output stage
    builder.start_sub_folder("OutputStage")
    builder.add_numeric_switch("ReachedHold")
    builder.end_sub_folder()
    # Wiring
    builder.add_link("Counter", "out", "Reached_GE_Target", "inA")
    builder.add_link("Target", "out", "Reached_GE_Target", "inB")
    builder.add_link("Reached_GE_Target", "out", "NotReached", "in")
    builder.add_link("Enable", "out", "Enable_AND_NotReached", "inA")
    builder.add_link("NotReached", "out", "Enable_AND_NotReached", "inB")
    builder.add_link("Enable_AND_NotReached", "out", "Enable_AND_Hold", "inA")
    builder.add_link("PulseNot", "out", "Enable_AND_Hold", "inB")
    builder.add_link("Enable_AND_Hold", "out", "TickDelay", "in")
    builder.add_link("TickDelay", "out", "TickPulse", "in")
    builder.add_link("TickPulse", "out", "PulseNot", "in")
    builder.add_link("Counter", "out", "UnitDelay", "in")
    builder.add_link("UnitDelay", "out", "CounterPlusStep", "inA")
    builder.add_link("Step", "out", "CounterPlusStep", "inB")
    builder.add_link("TickPulse", "out", "PulseGate", "inSwitch")
    builder.add_link("CounterPlusStep", "out", "PulseGate", "inTrue")
    builder.add_link("UnitDelay", "out", "PulseGate", "inFalse")
    builder.add_link("PulseGate", "out", "Counter", "in16")
    builder.add_link("Counter", "out", "Counter_Out", "in16")
    # Save
    out_path = tmp_path / "test_periodic_trigger.bog"
    builder.save(str(out_path))
    assert out_path.exists()


def _tournament_find_max(
    builder: BogFolderBuilder, inputs: list[str], rank_label: str
) -> tuple[str | None, list[str]]:
    """Internal helper for the top_five_of_fifteen test (mimics script logic)."""
    if not inputs:
        return None, []
    if len(inputs) == 1:
        return inputs[0], []
    current = inputs[:]
    losers: list[str] = []
    round_num = 1
    while len(current) > 1:
        next_round: list[str] = []
        for i in range(0, len(current) - 1, 2):
            a = current[i]
            b = current[i + 1]
            max_node, min_node = _compare_pair(
                builder, a, b, f"{rank_label}_R{round_num}_P{i//2}"
            )
            next_round.append(max_node)
            losers.append(min_node)
        if len(current) % 2 == 1:
            next_round.append(current[-1])
        current = next_round
        round_num += 1
    return current[0], losers


def test_workbench_top_five_of_fifteen(tmp_path: Path) -> None:
    """Recreate the top_five_of_fifteen example exactly."""
    builder = BogFolderBuilder("FindTop5Of15Dampers")
    inputs = [f"VAV_Damper_{i}" for i in range(1, 16)]
    for i, name in enumerate(inputs):
        builder.add_numeric_writable(name, default_value=float((i + 1) * 10))
    builder.add_numeric_writable("I_ignore_var", default_value=1.0)
    for rank in range(1, 6):
        builder.add_numeric_writable(f"Rank_{rank}_Highest")
    builder.add_numeric_writable("Filtered_Max")
    remaining = inputs[:]
    winners: list[str] = []
    for rank in range(1, 6):
        if not remaining:
            break
        builder.start_sub_folder(f"Rank_{rank}")
        winner, losers = _tournament_find_max(builder, remaining, f"Rank{rank}")
        builder.end_sub_folder()
        if winner:
            winners.append(winner)
            builder.add_link(winner, "out", f"Rank_{rank}_Highest", "in16")
        remaining = losers
    builder.start_sub_folder("SelectionLogic")
    builder.add_numeric_select("Ignore")
    builder.end_sub_folder()
    if winners:
        for i, winner_name in enumerate(winners):
            target_slot = f"in{chr(65 + i)}"
            builder.add_link(winner_name, "out", "Ignore", target_slot)
        builder.add_link("I_ignore_var", "out", "Ignore", "select")
        builder.add_link("Ignore", "out", "Filtered_Max", "in16")
    out_path = tmp_path / "top_five_of_fifteen.bog"
    builder.save(str(out_path))
    assert out_path.exists()
