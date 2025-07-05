# pybog
To create a Python library that can parse, analyze, manipulate, and programmatically generate Tridium Niagara .bog files. This will enable automation for tasks like bulk component creation, configuration updates, and template generation without using Niagara Workbench.

## Parse existing .bogs
```bash
python examples/main_parser.py examples/ClgControlLogic.bog --debug
```

## Make a .bog with py script
```bash
python examples/main_builder_g36.py 
```

## FUTURE
Get creative with AI agents in lessons learned.


```
pybog/
├── src/
│   ├── bog_parser.py      # Phase 1: Code to read and parse .bog files
│   ├── bog_builder.py     # Phase 2: Code to create .bog files from scratch
│   └── __init__.py
├── examples/
│   ├── sample.bog         # A generic .bog file to use for testing
│   ├── main_parser.py     # Example script showing how to use the parser
│   └── main_builder.py    # Example script showing how to use the builder
├── tests/
│   ├── test_parser.py
│   └── test_builder.py
└── README.md              # This project plan
```

Here is a significantly improved and well-structured `README.md` for your **pybog** project, using `<details>` tags for easier navigation and a professional layout without emojis:

---

```markdown
# pybog: Programmatic BOG File Generator for Tridium Niagara

`pybog` is a Python toolkit that enables you to **parse**, **analyze**, **manipulate**, and **generate** `.bog` files used in Tridium Niagara. This allows you to automate wire sheet logic and component creation without relying on Niagara Workbench.

---

## Table of Contents

<details>
  <summary><strong>📂 Project Overview</strong></summary>

`pybog` consists of a parser and builder to work with `.bog` files, which are Niagara's ZIP-encoded configuration files.

```

pybog/
├── src/
│   ├── bog\_parser.py       # Read and parse .bog files
│   ├── bog\_builder.py      # Create new .bog files from scratch
├── examples/
│   ├── main\_parser.py      # Run the parser on existing BOGs
│   ├── main\_builder\_g36.py # Create a sample G36 logic sequence
├── tests/                  # (optional) Add tests here
└── README.md               # This file

```

</details>

<details>
  <summary><strong>🔍 Parsing Existing .bog Files</strong></summary>

You can parse and inspect `.bog` files using `main_parser.py`.

### 🔧 Example Usage

```bash
python examples/main_parser.py examples/YourBogFileName.bog
python examples/main_parser.py examples/YourBogFileName.bog --debug
```

This will:

* Load the `.bog` as a zip archive
* Find the main logic folder
* List out component names and types
* (Optional) Print full XML tree in debug mode

</details>

<details>
  <summary><strong>🛠 Creating .bog Files Programmatically</strong></summary>

You can generate Niagara wire sheet logic using the builder API.

### 📌 Sample Code

```python
from src.bog_builder import BogFolderBuilder

builder = BogFolderBuilder('MyLogicSheet')

# Add a writable setpoint
setpoint = builder.add_component('control:NumericWritable', 'ZoneSetpoint')

# Add a PID loop with configured properties
pid = builder.add_component(
    'kitControl:LoopPoint', 'ZonePID',
    properties={'proportionalConstant': '2.5', 'integralConstant': '0.2'}
)

# Wire the setpoint to the PID
builder.add_link(
    source_comp_handle=setpoint.get('h'), source_slot='out',
    target_comp_handle=pid.get('h'), target_slot='setpoint'
)

builder.save('examples/my_logic.bog')
```

### 🔄 Auto-Layout

The builder automatically places components with typewriter-style layout. You can call:

```python
builder.new_row()  # Start next row of logic blocks
```

</details>

<details>
  <summary><strong>📘 G36 Logic Builder Example</strong></summary>

`main_builder_g36.py` demonstrates how to construct a Guideline 36 Duct Static Reset sequence:

### Run it:

```bash
python examples/main_builder_g36.py
```

### Output:

* Generates `examples/generated_g36_logic.bog`
* You can drag this file into Niagara Workbench

### Components Used:

* `kitControl:Maximum` for damper max logic
* `kitControl:LoopPoint` for PID
* `control:NumericWritable` for output setpoint
* `control:BooleanWritable` for fan status

</details>

<details>
  <summary><strong>📚 Component Reference (kitControl)</strong></summary>

The following `kitControl` components are supported:

#### Alarm

* `kitControl:ChangeOfStateCountAlarmExt`
* `kitControl:ElapsedActiveTimeAlarmExt`
* `kitControl:LoopAlarmExt`

#### Constants

* `kitControl:BooleanConst`, `NumericConst`, `StringConst`, etc.

#### Conversions

* `kitControl:StatusNumericToInt`, `EnumToStatusEnum`, etc.

#### HVAC / Energy

* `kitControl:LoopPoint`, `OptimizedStartStop`, `NightPurge`, etc.

#### Logic / Math

* `kitControl:And`, `Or`, `Not`, `Add`, `Multiply`, etc.

#### Select / String / Timer / Util

* Full list provided in the original readme or source code

</details>

<details>
  <summary><strong>📜 License</strong></summary>

This project is open source under the [MIT License](LICENSE).

You are free to use, modify, and distribute this software with proper attribution.

</details>

---



## 📍 License

This project is open source and made available under the permissive [MIT License](LICENSE), allowing for reuse, modification, and distribution with attribution.
