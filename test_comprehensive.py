#!/usr/bin/env python3
"""Comprehensive test script to explore all pybog capabilities and wire sheet generation."""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from bog_builder import BogFolderBuilder

def test_all_components():
    """Test and document all available components and their capabilities."""
    
    # Create a new BOG builder
    builder = BogFolderBuilder("TestAllComponents", debug=True)
    
    # Test 1: Basic Math Components
    print("Testing Math Components...")
    builder.start_sub_folder("MathOperations")
    
    # Add inputs
    builder.add_numeric_writable("Input_A", 10.0)
    builder.add_numeric_writable("Input_B", 20.0)
    builder.add_numeric_writable("Input_C", 30.0)
    
    # Test all math operations
    builder.add_component("kitControl:Add", "Adder")
    builder.add_component("kitControl:Subtract", "Subtractor")
    builder.add_component("kitControl:Multiply", "Multiplier")
    builder.add_component("kitControl:Divide", "Divider")
    builder.add_component("kitControl:Average", "Averager")
    builder.add_component("kitControl:Minimum", "MinFinder")
    builder.add_component("kitControl:Maximum", "MaxFinder")
    
    # Link inputs to operations
    builder.add_link("Input_A", "out", "Adder", "inA")
    builder.add_link("Input_B", "out", "Adder", "inB")
    
    builder.add_link("Input_A", "out", "Subtractor", "inA")
    builder.add_link("Input_B", "out", "Subtractor", "inB")
    
    # Output writables
    builder.add_numeric_writable("Add_Result")
    builder.add_numeric_writable("Subtract_Result")
    
    builder.add_link("Adder", "out", "Add_Result", "in16")
    builder.add_link("Subtractor", "out", "Subtract_Result", "in16")
    
    builder.end_sub_folder()
    
    # Test 2: Boolean Logic Components
    print("Testing Boolean Logic Components...")
    builder.start_sub_folder("BooleanLogic")
    
    builder.add_boolean_writable("Bool_Input_1", True)
    builder.add_boolean_writable("Bool_Input_2", False)
    
    builder.add_component("kitControl:And", "AndGate")
    builder.add_component("kitControl:Or", "OrGate")
    builder.add_component("kitControl:Xor", "XorGate")
    builder.add_component("kitControl:Not", "NotGate")
    
    builder.add_link("Bool_Input_1", "out", "AndGate", "inA")
    builder.add_link("Bool_Input_2", "out", "AndGate", "inB")
    
    builder.add_link("Bool_Input_1", "out", "OrGate", "inA")
    builder.add_link("Bool_Input_2", "out", "OrGate", "inB")
    
    builder.add_link("Bool_Input_1", "out", "NotGate", "in")
    
    builder.add_boolean_writable("And_Result")
    builder.add_boolean_writable("Or_Result")
    builder.add_boolean_writable("Not_Result")
    
    builder.add_link("AndGate", "out", "And_Result", "in16")
    builder.add_link("OrGate", "out", "Or_Result", "in16")
    builder.add_link("NotGate", "out", "Not_Result", "in16")
    
    builder.end_sub_folder()
    
    # Test 3: Comparison Components
    print("Testing Comparison Components...")
    builder.start_sub_folder("Comparisons")
    
    builder.add_numeric_writable("Compare_A", 25.0)
    builder.add_numeric_writable("Compare_B", 30.0)
    
    builder.add_component("kitControl:GreaterThan", "GT_Comparator")
    builder.add_component("kitControl:LessThan", "LT_Comparator")
    builder.add_component("kitControl:Equal", "EQ_Comparator")
    builder.add_component("kitControl:GreaterThanEqual", "GTE_Comparator")
    builder.add_component("kitControl:LessThanEqual", "LTE_Comparator")
    
    builder.add_link("Compare_A", "out", "GT_Comparator", "inA")
    builder.add_link("Compare_B", "out", "GT_Comparator", "inB")
    
    builder.add_link("Compare_A", "out", "LT_Comparator", "inA")
    builder.add_link("Compare_B", "out", "LT_Comparator", "inB")
    
    builder.add_link("Compare_A", "out", "EQ_Comparator", "inA")
    builder.add_link("Compare_B", "out", "EQ_Comparator", "inB")
    
    builder.add_boolean_writable("GT_Result")
    builder.add_boolean_writable("LT_Result")
    builder.add_boolean_writable("EQ_Result")
    
    builder.add_link("GT_Comparator", "out", "GT_Result", "in16")
    builder.add_link("LT_Comparator", "out", "LT_Result", "in16")
    builder.add_link("EQ_Comparator", "out", "EQ_Result", "in16")
    
    builder.end_sub_folder()
    
    # Test 4: Control Components
    print("Testing Control Components...")
    builder.start_sub_folder("ControlLogic")
    
    # Test Numeric Switch
    builder.add_boolean_writable("Switch_Control", False)
    builder.add_numeric_writable("True_Value", 100.0)
    builder.add_numeric_writable("False_Value", 0.0)
    
    builder.add_component("kitControl:NumericSwitch", "NumSwitch")
    builder.add_link("Switch_Control", "out", "NumSwitch", "inSwitch")
    builder.add_link("True_Value", "out", "NumSwitch", "inTrue")
    builder.add_link("False_Value", "out", "NumSwitch", "inFalse")
    
    builder.add_numeric_writable("Switch_Output")
    builder.add_link("NumSwitch", "out", "Switch_Output", "in16")
    
    # Test Latches
    builder.add_component("kitControl:BooleanLatch", "BoolLatch")
    builder.add_component("kitControl:NumericLatch", "NumLatch")
    
    # Test Delays
    builder.add_component("kitControl:BooleanDelay", "BoolDelay")
    builder.add_component("kitControl:NumericDelay", "NumDelay")
    
    # Test Counter
    builder.add_component("kitControl:Counter", "Counter1", {
        "countIncrement": 1.0,
        "initialValue": 0.0
    })
    
    builder.add_boolean_writable("CountUp_Trigger", False)
    builder.add_boolean_writable("CountDown_Trigger", False)
    builder.add_link("CountUp_Trigger", "out", "Counter1", "countUp")
    builder.add_link("CountDown_Trigger", "out", "Counter1", "countDown")
    
    builder.add_numeric_writable("Counter_Output")
    builder.add_link("Counter1", "out", "Counter_Output", "in16")
    
    builder.end_sub_folder()
    
    # Test 5: Time-based Components
    print("Testing Time-based Components...")
    builder.start_sub_folder("TimeBasedLogic")
    
    # Test OneShot
    builder.add_component("kitControl:OneShot", "OneShot1", {
        "time": "1000"  # 1 second
    })
    
    # Test MultiVibrator
    builder.add_component("kitControl:MultiVibrator", "Oscillator", {
        "period": "2000"  # 2 seconds
    })
    
    # Test SineWave
    builder.add_component("kitControl:SineWave", "SineGen")
    
    builder.add_boolean_writable("OneShot_Trigger", False)
    builder.add_link("OneShot_Trigger", "out", "OneShot1", "in")
    
    builder.add_boolean_writable("OneShot_Output")
    builder.add_boolean_writable("Oscillator_Output")
    builder.add_numeric_writable("Sine_Output")
    
    builder.add_link("OneShot1", "out", "OneShot_Output", "in16")
    builder.add_link("Oscillator", "out", "Oscillator_Output", "in16")
    builder.add_link("SineGen", "out", "Sine_Output", "in16")
    
    builder.end_sub_folder()
    
    # Test 6: Enum Components
    print("Testing Enum Components...")
    builder.start_sub_folder("EnumLogic")
    
    # Define an enum range for modes
    builder.define_enum_range("OperationMode", {
        "Off": 0,
        "Auto": 1,
        "Manual": 2,
        "Override": 3
    })
    
    builder.add_enum_writable_by_name("Mode_Selector", "OperationMode", "Auto")
    builder.add_enum_const_by_name("Default_Mode", "OperationMode", "Off")
    
    builder.end_sub_folder()
    
    # Test 7: Advanced Control - PID Loop
    print("Testing PID Loop...")
    builder.start_sub_folder("PIDControl")
    
    builder.add_component("kitControl:LoopPoint", "PID_Loop", {
        "loopEnable": True,
        "controlledVariable": 72.0,
        "setpoint": 75.0,
        "loopAction": 1,
        "proportionalConstant": 2.0,
        "integralConstant": 0.5
    })
    
    builder.add_numeric_writable("Process_Variable", 72.0)
    builder.add_numeric_writable("Setpoint", 75.0)
    builder.add_boolean_writable("Enable_PID", True)
    
    builder.add_link("Process_Variable", "out", "PID_Loop", "controlledVariable")
    builder.add_link("Setpoint", "out", "PID_Loop", "setpoint")
    builder.add_link("Enable_PID", "out", "PID_Loop", "loopEnable")
    
    builder.add_numeric_writable("PID_Output")
    builder.add_link("PID_Loop", "out", "PID_Output", "in16")
    
    builder.end_sub_folder()
    
    # Test 8: Reset/Scaling Component
    print("Testing Reset/Scaling...")
    builder.start_sub_folder("Scaling")
    
    builder.add_component("kitControl:Reset", "Scaler", {
        "inputLowLimit": 0.0,
        "inputHighLimit": 100.0,
        "outputLowLimit": 0.0,
        "outputHighLimit": 10.0
    })
    
    builder.add_numeric_writable("Raw_Input", 50.0)
    builder.add_link("Raw_Input", "out", "Scaler", "inA")
    
    builder.add_numeric_writable("Scaled_Output")
    builder.add_link("Scaler", "out", "Scaled_Output", "in16")
    
    builder.end_sub_folder()
    
    # Test 9: Reduction Blocks (automatic tree generation)
    print("Testing Reduction Blocks...")
    builder.start_sub_folder("ReductionExamples")
    
    # Create many inputs for reduction
    input_names = []
    for i in range(10):
        name = f"Sensor_{i+1}"
        builder.add_numeric_writable(name, float(i * 10))
        input_names.append(name)
    
    # Create average reduction block
    builder.add_reduction_block("Average", "Average_Output", input_names[:6])
    
    # Create minimum reduction block
    builder.add_reduction_block("Minimum", "Min_Output", input_names[3:8])
    
    # Create maximum reduction block
    builder.add_reduction_block("Maximum", "Max_Output", input_names)
    
    builder.end_sub_folder()
    
    # Save the BOG file
    output_path = r"C:\Users\tech\Projects\pybog\data\outputs\test_all_components.bog"
    builder.save(output_path)
    print(f"\nBOG file saved to: {output_path}")
    
    # Print summary
    print("\n=== Summary ===")
    print(f"Total components created: {len(builder._components)}")
    print(f"Total links created: {len(builder._links)}")
    print(f"Total sub-folders: {len(builder._sub_folders)}")
    
    # List all component types used
    component_types = set(comp['type'] for comp in builder._components.values())
    print(f"\nComponent types used ({len(component_types)}):")
    for comp_type in sorted(component_types):
        count = sum(1 for c in builder._components.values() if c['type'] == comp_type)
        print(f"  - {comp_type}: {count}")
    
    return builder

if __name__ == "__main__":
    print("=== PyBOG Comprehensive Component Test ===\n")
    test_all_components()
