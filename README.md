# pybog: A Python Toolkit for Niagara BOG & DIST Files

This project provides a Python library to **analyze**, **parse**, and **generate** Tridium Niagara `.bog` and `.dist` files. It enables developers, controls engineers, and AI systems to work with Niagara control logic **offline**, without requiring Workbench.

The ultimate goal of the project is to empower **AI-assisted generation of Niagara wiresheet logic**—ranging from simple control sequences to complex optimization routines such as those defined by **ASHRAE Guideline 36**. By providing structured programmatic access to Niagara logic, the tools support automation, advanced supervisory control strategies, and scalable logic deployment across building automation systems.

---

## 🔍 Features

- **Parse `.bog` Files**: Load and inspect logic stored in Niagara `.bog` files (ZIPs with XML).
- **Explore `.dist` Files**: Automatically extract `config.bog` from station backups and analyze the full logic setup.
- **Output to JSON**: Convert Niagara logic into structured, LLM-friendly JSON for further automation or training.
- **Component Graphs**: Identify components, links, and source code blocks (e.g. Java snippets in Program Objects).
- **Zero Dependencies**: Works with Python’s standard library. No installation needed beyond Python.

---

## 📁 Project Layout
* TODO make more robust cheet sheet on best practices.

```bash
pybog/                          <-- run python commands from here
├── examples/                   <-- put your bog and dist files in here
│   ├── Adder.bog
│   ├── backup_Diggs_RTU9.dist
│   ├── main_analyzer.py
│   └── main_builder.py
├── pdf/                        <-- KitControl reference from Niagara
│   └── docKitControl.pdf      
├── context_engineering/        <-- Cheet sheet for AI to use if you upload the text file
│   └── llm_bog_instructions.text
├── src/                        <-- helper functions
│   ├── analyzer.py
│   └── bog_builder.py
└── README.md
````

---

## ✅ How to Use

### 1. Analyze a `.bog` or `.dist` File

Run the analyzer and save results as either a readable text file or JSON.

```bash
python examples/main_analyzer.py <path_to_file.bog|.dist> -o <output_file> [--debug] [--list-files]
```

#### Examples:

```bash
# Convert a BOG file to structured JSON
python examples/main_analyzer.py examples/Adder.bog -o Adder.json

# Extract logic from a full station backup
python examples/main_analyzer.py examples/backup_Diggs_RTU9.dist -o digg_rtu9_analysis.json

# List all files in a station backup
python examples/main_analyzer.py examples/backup_Diggs_RTU9.dist --list-files
```

---

## 💡 LLM Integration

The output JSON includes:

* Component names, types, and properties
* Wire sheet link structure
* Any embedded Java source (for Program Objects)
* All handles (IDs) and their resolved names

You can use this data to:

* Summarize Niagara logic
* Generate prompts to recreate it using a builder
* Train models on real-world examples (e.g., Diggs RTU9)

---

## 🏗️ Coming Soon: BOG Builder

The builder will allow users to define logic via Python and export `.bog` files:

```python
from src.bog_builder import BogFolderBuilder

builder = BogFolderBuilder("DemoLogic")
builder.add_component("kitControl:BooleanConst", "MyOnSignal", properties={"out": "true"})
builder.save("examples/generated.bog")
```

---

## 🧱 Component Library (kitControl)

Reference logic building blocks from Niagara’s kitControl palette are documented in `pdf/docKitControl.pdf`.

---

## 📄 License

MIT License — free for reuse with attribution.

