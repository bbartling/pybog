# pybog: A Python Toolkit for Niagara BOG & DIST Files

This project provides a Python library to programmatically **parse**, **analyze**, **manipulate**, and **generate** Tridium Niagara `.bog` files. It also includes tools to explore `.dist` station backup archives, enabling large-scale analysis and automation for Niagara systems without needing Workbench.

---

## Features

- **Parse .bog Files**: Read any `.bog` file (ZIP archive containing `file.xml`) and inspect its contents.
- **Build .bog Files**: Programmatically create complex wire sheets with components, properties, and links using a clean API.
- **Explore .dist Files**: Analyze station backup `.dist` archives to find and extract the main `config.bog` and logic.
- **LLM-Friendly Output**: Generate clean, human-readable summaries from station backups — ideal for AI analysis and documentation.
- **No External Libraries**: Uses Python’s standard library only — no `pip install` needed.

---

## Project Structure

```

pybog/
├── src/
│   ├── bog\_parser.py        # Parse .bog files
│   ├── bog\_builder.py       # Build .bog files
│   └── dist\_explorer.py     # Analyze .dist station backups
├── examples/
│   ├── main\_parser.py         # Parse a .bog file
│   ├── main\_builder.py        # Build logic into a .bog
│   └── main\_dist\_explorer.py  # Explore .dist files
└── README.md

```

---

## Usage

<details>
<summary><strong>1. Parsing a .bog File</strong></summary>

Use `main_parser.py` to inspect the contents of a `.bog` file.

### Command:
```bash
python examples/main_parser.py <path_to_bog_file> [--debug]
````

### Example:

```bash
python examples/main_parser.py examples/ClgControlLogic.bog
python examples/main_parser.py examples/ClgControlLogic.bog --debug
```

* Finds the logic folder.
* Lists components and types.
* Optionally prints the entire XML tree (debug mode).

</details>

<details>
<summary><strong>2. Building a .bog File</strong></summary>

Use `main_builder.py` to generate wire sheet logic.

### Command:

```bash
python examples/main_builder.py <type> [-o <output_file_name>]
```

#### Arguments:

* `<type>`: Type of logic to build (`g36` or `chiller`)
* `-o`, `--output`: Optional output file name (default: `generated.bog`)

### Examples:

```bash
python examples/main_builder.py g36 -o g36.bog
python examples/main_builder.py chiller
```

The `.bog` file will be saved to the `examples/` directory.

</details>

<details>
<summary><strong>3. Exploring a .dist Station Backup</strong></summary>

Use `main_dist_explorer.py` to extract and summarize a full Niagara station backup.

### Command:

```bash
python examples/main_dist_explorer.py <path_to_dist_file> [-o <output_file>] [-l]
```

#### Arguments:

* `<file>`: Path to the `.dist` station backup file
* `-o`, `--output`: Optional text output file (default: `station_analysis.txt`)
* `-l`, `--list-files`: Lists all files inside the archive and exits

### Examples:

```bash
python examples/main_dist_explorer.py examples/backup_Diggs_RTU9.dist -o diggs_rtu9_analysis.txt
python examples/main_dist_explorer.py examples/backup_Berry.dist --list-files
```

</details>

<details>
<summary><strong>4. Building .bog Logic via Code</strong></summary>

### Sample Usage:

```python
from src.bog_builder import BogFolderBuilder

builder = BogFolderBuilder("MyLogicSheet")

setpoint = builder.add_component("control:NumericWritable", "ZoneSetpoint")

pid = builder.add_component(
    "kitControl:LoopPoint", "ZonePID",
    properties={"proportionalConstant": "2.5", "integralConstant": "0.2"}
)

builder.add_link(
    source_comp_handle=setpoint.get("h"), source_slot="out",
    target_comp_handle=pid.get("h"), target_slot="setpoint"
)

builder.save("examples/my_first_logic.bog")
```

Supports auto-layout and `new_row()` for visual structure.

</details>

<details>
<summary><strong>5. Component Reference: kitControl</strong></summary>

A full list of creatable components supported by the builder, based on Niagara’s documentation.

### Alarm Components

* `kitControl:ChangeOfStateCountAlarmExt`
* `kitControl:ElapsedActiveTimeAlarmExt`
* `kitControl:LoopAlarmExt`
* `kitControl:AlarmCountToRelay`

### Constants Components

* `kitControl:BooleanConst`, `EnumConst`, `NumericConst`, `StringConst`

### Conversion Components

* `kitControl:StatusBooleanToBoolean`, `StatusEnumToInt`, `NumericUnitConverter`, etc.

### Energy Components

* `kitControl:OptimizedStartStop`, `NightPurge`, `SetpointLoadShed`, etc.

### HVAC Components

* `kitControl:LoopPoint`, `Tstat`, `SequenceBinary`, `LeadLagRuntime`, etc.

### Latch, Logic, Math, Timer, String, Select, Util Components

* All included from the original Niagara kitControl PDF

</details>

---

## License

This project is licensed under the permissive [MIT License](LICENSE), allowing reuse, modification, and distribution with attribution.

