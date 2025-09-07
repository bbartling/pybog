# pybog: A Python Toolkit for Niagara BOG & DIST Files

`bog_builder` is a Python package for constructing Niagara Baja Object Graphs `.bog` files programmatically. The goal is for AI to assist human controls engineers in rapidly prototyping complex HVAC sequencing within wire sheet logic. If the software engineering community can prototype quickly, why shouldn’t the controls engineering community be able to do the same?

---

<details><summary><strong>Python Project Setup</strong></summary>

I use **WSL (Windows Subsystem for Linux)** but it make work just fine on ordinary Windows or Mac. Generating `bogs` can be done easily without setting up Python environments as shown further below via "ChatGPT Agent" mode and **The Bog Maker 4000** website. Both examples are demo'd on YouTube.

```bash
pip install pybog
# or keep up to date
pip install pybog --upgrade
```

### Contribute to `pybog` via developing a local Python package
```bash
pip install .
```

To uninstall `bog_builder` if developing:
```bash
pip uninstall bog_builder
```

### Run tests
```bash
pytest
```
Make a Git PR — and if it is a mega‑makeover beyond submitting [examples](https://github.com/bbartling/pybog/tree/develop/examples) Python files, please give me a heads‑up first.
</details>

---

<details><summary><strong>KitControl API Usage Examples</strong></summary>

The following examples illustrate how to instantiate and wire commonly used **kitControl** components using the `BogFolderBuilder` API. Each block lists its Niagara type, the corresponding builder method, input and output slot names, and a minimal code snippet showing how to create and link the component.

#### Add (Math)
- **Niagara Type:** `kitControl:Add`  
- **Builder Method:** `add_add(name: str)`  
- **Inputs:** `inA`, `inB`, `inC`, `inD`  
- **Output:** `out`  

```python
# Create two numeric writables and an Add block, then link them.
builder.add_numeric_writable("Input1", 50.0)
builder.add_numeric_writable("Input2", 30.0)
builder.add_add("Total")
builder.add_link("Input1", "out", "Total", "inA")
builder.add_link("Input2", "out", "Total", "inB")
builder.add_link("Total", "out", "SomeOutputWritable", "in16")
```

#### NumericSwitch (Util)
- **Niagara Type:** `kitControl:NumericSwitch`  
- **Builder Method:** `add_numeric_switch(name: str)`  
- **Inputs:** `inSwitch` (control), `inTrue` (value when true), `inFalse` (value when false)  
- **Output:** `out`  

```python
# Route between two values based on a BooleanWritable.
builder.add_boolean_writable("Enable", True)
builder.add_numeric_writable("LowValue", 0.0)
builder.add_numeric_writable("HighValue", 100.0)
builder.add_numeric_switch("ModeSwitch")
builder.add_link("Enable", "out", "ModeSwitch", "inSwitch")
builder.add_link("HighValue", "out", "ModeSwitch", "inTrue")
builder.add_link("LowValue", "out", "ModeSwitch", "inFalse")
```

#### GreaterThan (Logic)
- **Niagara Type:** `kitControl:GreaterThan`  
- **Builder Method:** `add_greater_than(name: str)`  
- **Inputs:** `inA`, `inB`  
- **Output:** `out`  

```python
# Compare two numeric values and produce a Boolean result.
builder.add_numeric_writable("TempA", 68.0)
builder.add_numeric_writable("TempB", 70.0)
builder.add_greater_than("IsWarmer")
builder.add_link("TempA", "out", "IsWarmer", "inA")
builder.add_link("TempB", "out", "IsWarmer", "inB")
# The 'out' slot on IsWarmer can be linked to a Boolean input on another block.
```
These examples mirror the tested calls found in the `kitControlIntrol.txt` context file and demonstrate how to map each widget’s slot names to the builder API.
</details>

---

<details><summary><strong>BogFolderBuilder Method Reference</strong></summary>

Unless noted otherwise, each method accepts a `name: str` for the component and optional `properties: dict` and `actions: dict` to customize behaviour.

- **Writable Points:** `add_numeric_writable`, `add_boolean_writable`, `add_enum_writable`  
  Create settable points for user inputs or final outputs. You can specify default values, precision, units or facets as needed.

- **Constants:** `add_numeric_const`, `add_boolean_const`, `add_enum_const`  
  Produce fixed numeric, boolean or enumerated values.

- **Switches & Selectors:** `add_numeric_switch`, `add_boolean_switch`, `add_numeric_select`  
  Route one of two or more values based on a control input.

- **Timers & Delays:** `add_numeric_delay`, `add_boolean_delay`, `add_one_shot`, `add_multi_vibrator`, `add_counter`  
  Provide transient or periodic behaviour—e.g., pulse generation, on/off delays, and counting.

- **Math:** `add_add`, `add_subtract`, `add_multiply`, `add_divide`, `add_average`, `add_minimum`, `add_maximum`, `add_sine_wave`, `add_reset`  
  Perform arithmetic or waveform generation.

- **Logic:** `add_and`, `add_or`, `add_xor`, `add_not`, `add_equal`, `add_not_equal`, `add_greater_than`, `add_greater_than_equal`, `add_less_than`, `add_less_than_equal`  
  Create boolean logic gates and comparisons.

- **Latches:** `add_boolean_latch`, `add_numeric_latch`  
  Hold a value until explicitly reset.

- **HVAC Helpers:** `add_lead_lag_cycles`, `add_lead_lag_runtime`, `add_loop_point`, `add_tstat`, `add_reset`  
  Encapsulate common control sequences such as lead/lag rotation or thermostat logic.

- **Enums & Schedules:** `add_enum_const`, `add_enum_writable`, `add_enum_writable_by_name`, `add_enum_const_by_name`, `add_boolean_schedule`, `add_numeric_schedule`, `add_enum_schedule`  
  Work with enumerated values and schedules.

- **Folder Management:** `start_sub_folder(name)`, `end_sub_folder()`  
  Organise your components into nested folders for readability.

- **Linking & Reduction:** `add_link(source, source_slot, target, target_slot)`, `add_reduction_block(block_type, final_output_name, input_names)`  
  Connect slots between components or generate trees of Average/Minimum/Maximum blocks from many inputs.

- **Saving:** `save(file_path)`  
  Write the assembled graph to a `.bog` file.

Refer to `bog_builder/builder.py` for complete argument descriptions and additional helpers.
</details>

---

<details><summary><strong>BogFolderBuilder API Overview</strong></summary>

High‑level methods for constructing components and wiring them together (selected signatures):

```python
add_numeric_writable(name: str, default_value: float = 0.0, precision: int = 2, units: str = "u:null")
add_boolean_writable(name: str, default_value: bool = False)
add_enum_writable(name: str, facets: str, default_value: str = "0")

add_numeric_switch(name: str)
add_boolean_switch(name: str)
add_numeric_select(name: str)

add_multi_vibrator(name: str, period_ms: str | int = "10000")
add_counter(name: str, count_increment: float = 1.0, precision: int | None = None, properties: dict | None = None)

add_add(name: str); add_subtract(name: str); add_multiply(name: str); add_divide(name: str)
add_average(name: str); add_minimum(name: str); add_maximum(name: str); add_sine_wave(name: str)

add_numeric_latch(name: str); add_boolean_latch(name: str)

add_numeric_delay(name: str, update_time: str | int | None = None, max_step_size: float | None = None)
add_boolean_delay(name: str, on_delay: str | int | None = None, off_delay: str | int | None = None)

add_numeric_const(name: str, value: float | None = None)
add_boolean_const(name: str, value: bool | None = None)
add_enum_const(name: str, facets: str | None = None, value: str | None = None)

# Logic gates
add_equal(); add_not_equal(); add_greater_than(); add_greater_than_equal()
add_less_than(); add_less_than_equal(); add_and(); add_or(); add_xor(); add_not()

# HVAC helpers
add_lead_lag_cycles(); add_lead_lag_runtime(); add_loop_point(); add_tstat(); add_reset()

# Utilities
add_one_shot(); start_sub_folder(name); end_sub_folder()
add_link(source_comp_name, source_slot, target_comp_name, target_slot, *, link_type="b:Link", converter_type=None)
add_reduction_block(block_type: {"Average","Minimum","Maximum"}, final_output_name: str, input_names: list[str])

# Save the BOG file
save(file_path: str)
```
These methods wrap the internal `_add_component` API and ensure parameters are validated for Niagara 4 wire‑sheet compatibility.
</details>

---

<details><summary><strong>Running Example Scripts with WSL</strong></summary>

Each example script can be executed directly in WSL to generate a `.bog` file and drop it into your Niagara Workbench `JENEsys` directory. All example Python files are also compiled into a text file and used for LLM context.

**Run a specific example from project root directory** — pass the Workbench path via `-o`:
```bash
python examples/bool_latch_play_ground.py -o /mnt/c/Users/ben/Niagara4.11/JENEsys
```
This creates:
```
/mnt/c/Users/ben/Niagara4.11/JENEsys/bool_latch_play_ground.bog
```

**Open Workbench** — import/open the generated `.bog` file under your `JENEsys` station.

**Tip:** To avoid typing `-o` each time, change the default in each script’s `argparse`:
```python
parser.add_argument(
  "-o",
  "--output_dir",
  default="/mnt/c/Users/ben/Niagara4.11/JENEsys",
  help="Output directory for the .bog file."
)
```
Now you can run:
```bash
python examples/bool_latch_play_ground.py
```
</details>

---

<details><summary><strong>Bog Builder Python API Example</strong></summary>

This is a code snip from `examples/subtract_simple.py` with optional `start_sub_folder` structures.

```python
builder = BogFolderBuilder("SubtractionLogic")

# --- Inputs ---
builder.add_numeric_writable(name="Input_A", default_value=100.0)
builder.add_numeric_writable(name="Input_B", default_value=40.0)

# --- Output ---
builder.add_numeric_writable(name="Difference")

builder.start_sub_folder("CalculationLogic")
builder.add_component(comp_type="kitControl:Subtract", name="Subtract")
builder.end_sub_folder()

builder.add_link("Input_A", "out", "Subtract", "inA")
builder.add_link("Input_B", "out", "Subtract", "inB")
builder.add_link("Subtract", "out", "Difference", "in16")

builder.save(output_path)
```
When run, it will create a `.bog` file that can be directly imported into Workbench. `pybog` automatically arranges a clean grid layout; subfolders are optional but help keep files organized.
</details>

---

<details><summary><strong>Write Your Own <code>.bog</code> File in XML from Scratch</strong></summary>

The script constructs the entire `.bog` XML as a single multi‑line string, defining components, properties, and links, then writes it to disk so Niagara can open it as a standard wiresheet.

Key takeaways:
- `<p>` tags represent components or slots (e.g., `out`, `fallback`); `<a>` tags represent actions (`set`, `override`).
- The `f` attribute controls behaviour: `f="s"` makes a slot settable; `f="h"` / `f="ho"` hides a slot or action (for read‑only points).
- Defaults require full `out` + `fallback` status definitions.
- `h="1"`, `h="2"`, etc., are unique handles for link endpoints.
- `wsAnnotation` positions blocks on the wiresheet according to a hierarchical grid strategy.
</details>

---

<details><summary><strong>Using ChatGPT Agent Mode to Build <code>.bog</code> Files</strong></summary>

**Workflow:** upload your project zip → describe the sequence → the Agent generates & runs the builder code → you download the resulting `.bog` for Workbench.

**Advantages**
- No API key required
- No local Python setup
- Fast prototyping in chat

**Tips**
- Be specific with setpoints, deadbands, counts, and block names.
- Validate in Workbench and iterate as needed.
</details>

---

<details><summary><strong>Generate Context Text Files</strong></summary>

The `context/` directory contains LLM‑formatted docs built from `examples/`.

- `llms.txt` — sitemap of example files.
- `llms-full.txt` — concatenation of all example sources with clear delimiters (can exceed 20k tokens).

Generate:
```bash
python src/bog_builder/generate_llm_docs.py --examples examples --output context
```
</details>

---

<details><summary><strong>Traversing Baja Object Graphs</strong></summary>

Niagara stations are directed graphs. When parsing raw XML from `.bog`/`.dist`, follow these practices:

- Parse once, traverse many (cache `ElementTree` root).
- Use BFS/DFS with a visited set (components have unique `h` handles).
- Follow containment and `b:Link` connections.
- Build a handle→name map to resolve `h:` ords.
- Group/search by palette (e.g., `kitControl:Add`).

**Analyzer Class**
- Parse archive → flat JSON (components, properties, links).
- Build handle map.
- Helpers to count kitControl blocks and plot bar/pie charts.

**Comparator Class**
- Diff two archives (`analyzer compare A.bog B.bog`): report adds/removes/modified, including link/converter changes.

**Future**
- Simple Flask UI to upload two files and view a color‑coded diff.
</details>

---

<details><summary><strong>Example Output</strong></summary>

Bar chart `kitcontrol_counts_bar.png` and pie chart `kitcontrol_counts_pie.png` help visualize palette usage and block counts.
</details>

---

<details><summary><strong>Component Library (kitControl)</strong></summary>

Reference logic building blocks from Niagara’s kitControl palette are documented in `pdf/docKitControl.pdf`.
</details>

---

<details><summary><strong>License</strong></summary>

MIT License — free for reuse with attribution. Any files generated here are provided strictly for research and educational purposes. All outputs are delivered “as‑is,” with no guarantees of accuracy, safety, or fitness for any application. Neither the pybog project nor its creator accepts any responsibility or liability under any circumstances. By generating or using a `.bog` file produced by this project, you agree that you assume all risks and full responsibility for any outcomes—including, but not limited to, personal injury, loss of life, financial loss, equipment damage, or mechanical system failures. If you choose to use these files in any way, you do so entirely at your own risk.
</details>

---

## API Reference (kitControl Widgets & BogFolderBuilder)

Below is a summary of available kitControl widgets exposed through the `BogFolderBuilder` along with usage signatures and input/output slots. Use the checkboxes to track which widgets are implemented vs. pending.

<details><summary><strong>KitControl Widget Implementation Checklist</strong></summary>

### Alarm
- [ ] ChangeOfStateCountAlarmExt
- [ ] ElapsedActiveTimeAlarmExt
- [ ] LoopAlarmExt
- [ ] AlarmCountToRelay

### Constants
- [x] NumericConst
- [x] BooleanConst
- [x] EnumConst
- [ ] StringConst

### Conversion
- [ ] StatusBooleanToBoolean
- [ ] StatusEnumToEnum
- [ ] StatusEnumToInt
- [ ] StatusNumericToDouble
- [ ] StatusNumericToFloat
- [ ] StatusNumericToInt
- [ ] BooleanToStatusBoolean
- [ ] EnumToStatusEnum
- [ ] IntToStatusNumeric
- [ ] LongToStatusNumeric
- [ ] StringToStatusString
- [ ] StatusEnumToStatusBoolean
- [ ] StatusEnumToStatusNumeric
- [ ] StatusNumericToStatusEnum
- [ ] StatusNumericToStatusString
- [ ] StatusStringToStatusNumeric
- [ ] NumericUnitConverter

### Energy
- [ ] DegreeDays
- [ ] ElectricalDemandLimit
- [ ] NightPurge
- [ ] OptimizedStartStop
- [ ] OutsideAirOptimization
- [ ] Psychrometric
- [ ] SetpointLoadShed
- [ ] SetpointOffset
- [ ] ShedControl
- [ ] SlidingWindowDemandCalc

### HVAC
- [x] LeadLagCycles
- [x] LeadLagRuntime
- [x] LoopPoint
- [x] Tstat
- [ ] InterstartDelayControl
- [ ] InterstartDelayMaster
- [ ] RaiseLower
- [ ] SequenceBinary
- [ ] SequenceLinear

### Latch
- [x] BooleanLatch
- [x] NumericLatch
- [ ] EnumLatch
- [ ] StringLatch

### Logic
- [x] And
- [x] Or
- [x] Xor
- [x] Not
- [x] Equal
- [x] NotEqual
- [x] GreaterThan
- [x] GreaterThanEqual
- [x] LessThan
- [x] LessThanEqual

### Math
- [x] Add
- [x] Subtract
- [x] Multiply
- [x] Divide
- [x] Average
- [x] Minimum
- [x] Maximum
- [x] SineWave
- [x] Reset
- [ ] Modulus
- [ ] Power
- [ ] AbsValue
- [ ] ArcCosine
- [ ] ArcSine
- [ ] ArcTangent
- [ ] Cosine
- [ ] Exponential
- [ ] Factorial
- [ ] LogBase10
- [ ] LogNatural
- [ ] Negative
- [ ] SquareRoot
- [ ] Tangent

### Select
- [x] NumericSelect
- [ ] BooleanSelect
- [ ] EnumSelect
- [ ] StringSelect

### String
- [ ] StringConcat
- [ ] StringSubstring
- [ ] StringTrim
- [ ] StringIndexOf
- [ ] StringTest
- [ ] StringLen

### Timer
- [x] BooleanDelay
- [x] NumericDelay
- [x] OneShot
- [ ] CurrentTime
- [ ] TimeDifference

### Util
- [x] BooleanSwitch
- [x] NumericSwitch
- [x] MultiVibrator
- [x] Counter
- [ ] DigitalInputDemux
- [ ] EnumSwitch
- [ ] MinMaxAvg
- [ ] NumericBitAnd
- [ ] NumericBitOr
- [ ] NumericBitXor
- [ ] NumericToBitsDemux
- [ ] Ramp
- [ ] Random
- [ ] StatusDemux
- [ ] SineWave (already listed under Math)
</details>
