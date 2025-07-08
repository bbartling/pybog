# pybog: A Python Toolkit for Niagara BOG & DIST Files

![Leave Temp Snip](https://github.com/bbartling/n4-hvac-optimization-blocks/blob/develop/vr.png)



[🎥 Talk Shop With Ben on YouTube](https://www.youtube.com/@TalkShopWithBen)

This project provides a Python library to **analyze**, **parse**, and **generate** Tridium Niagara `.bog` and `.dist` files. It allows developers, controls engineers, and AI systems to work with Niagara control logic **offline**, without requiring Workbench.

By parsing complex JACE backup files into formats that AI/LLMs can understand, the tool enables powerful new workflows for **commissioning agents**, **field technicians**, and **consulting engineers**—such as conversing with an LLM to explain how the supervisory logic is structured.

The **ultimate goal** of the project is to enable AI to **generate Niagara Wiresheet logic**—from basic control sequences to advanced supervisory strategies, such as those defined in **ASHRAE Guideline 36**. Looking ahead, the tool aims to support **AI-driven translation** of control algorithms written in **Python**, **C++**, **JavaScript**, or other general-purpose, high-level C-style languages into Niagara Wiresheet logic. This would allow complex, algorithmic control logic authored by AI to be exported as `.bog` files, ready for human users to import, inspect, and test directly within the Niagara environment.

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

## 🐍 Python Tutorial: Write Your Own `.bog` File

The Python script operates by creating the entire XML structure of the Niagara .bog file as a single, multi-line text string. This string contains all the necessary tags to define each component, its properties, and the links between them. Finally, the script writes this complete XML string directly into a new file, which Niagara can then open and display as a standard wiresheet.

### ✨ Code Example

```python
xml_content = '''<bajaObjectGraph version="4.0" reversibleEncodingKeySource="none" FIPSEnabled="false" reversibleEncodingValidator="[null.1]=">
  <p t="b:UnrestrictedFolder" m="b=baja">
    <p n="MyAdderLogic" t="b:Folder">

      <!-- Input1: Settable point with default value -->
      <p n="Input1" t="control:NumericWritable" h="1" m="control=control">
        <p n="out" f="s" t="b:StatusNumeric">
          <p n="value" v="6.0"/>
          <p n="status" v="0;activeLevel=e:17@control:PriorityLevel"/>
        </p>
        <p n="fallback" t="b:StatusNumeric">
          <p n="value" v="6.0"/>
        </p>
        <a n="emergencyOverride" f="h"/>
        <a n="emergencyAuto" f="h"/>
        <a n="override" f="ho"/>
        <a n="auto" f="ho"/>
        <p n="wsAnnotation" t="b:WsAnnotation" v="10,10,8"/>
      </p>
      
      <!-- Input2: Settable point with default value -->
      <p n="Input2" t="control:NumericWritable" h="2" m="control=control">
        <p n="out" f="s" t="b:StatusNumeric">
          <p n="value" v="4.0"/>
          <p n="status" v="0;activeLevel=e:17@control:PriorityLevel"/>
        </p>
        <p n="fallback" t="b:StatusNumeric">
          <p n="value" v="4.0"/>
        </p>
        <a n="emergencyOverride" f="h"/>
        <a n="emergencyAuto" f="h"/>
        <a n="override" f="ho"/>
        <a n="auto" f="ho"/>
        <p n="wsAnnotation" t="b:WsAnnotation" v="10,20,8"/>
      </p>

      <!-- Add: Logic block with verbose links -->
      <p n="Add" t="kitControl:Add" h="3" m="kitControl=kitControl">
        <p n="wsAnnotation" t="b:WsAnnotation" v="20,15,8"/>
        <p n="Link" t="b:Link">
          <p n="sourceOrd" v="h:1"/>
          <p n="relationId" v="n:dataLink"/>
          <p n="sourceSlotName" v="out"/>
          <p n="targetSlotName" v="inA"/>
        </p>
        <p n="Link1" t="b:Link">
          <p n="sourceOrd" v="h:2"/>
          <p n="relationId" v="n:dataLink"/>
          <p n="sourceSlotName" v="out"/>
          <p n="targetSlotName" v="inB"/>
        </p>
      </p>
      
      <!-- Sum: Read-only point with Set action explicitly hidden -->
      <p n="Sum" t="control:NumericWritable" h="4" m="control=control">
        <p n="out" f="h"/>
        <a n="emergencyOverride" f="h"/>
        <a n="emergencyAuto" f="h"/>
        <a n="override" f="ho"/>
        <a n="auto" f="ho"/>
        <a n="set" f="ho"/>
        <p n="wsAnnotation" t="b:WsAnnotation" v="30,15,8"/>
        <p n="Link" t="b:Link">
          <p n="sourceOrd" v="h:3"/>
          <p n="relationId" v="n:dataLink"/>
          <p n="sourceSlotName" v="out"/>
          <p n="targetSlotName" v="in16"/>
        </p>
      </p>

    </p>
  </p>
</bajaObjectGraph>'''

with open("PyMadeAddr.bog", "w", encoding="utf-8") as f:
    f.write(xml_content)

```

### 📌 How it Works

* Each `<p>` tag represents a Niagara component or a **slot within a component** (like `out` or `fallback`). Each `<a>` tag represents an **action** on that component, like `set` or `override`.

* The `f` attribute (flags) is critical for controlling behavior. `f="s"` makes a slot **settable**, while `f="h"` or `f="ho"` **hides** a slot or action, which is how we create read-only points.

* To set a **default value**, the `out` and `fallback` slots must be fully defined as complex properties containing nested `<p n="value".../>` and `<p n="status".../>` tags.

* `h="1"`, `h="2"`, etc., are unique **handles** that links use to reference their source and target components.

* `wsAnnotation` controls the block's position on the wiresheet. The coordinates are calculated using our **Hierarchical Data Flow** strategy to ensure a clean, grid-based layout.

* The `Add` block's links use these handles to reference the `out` slots from `Input1` and `Input2` and connect them to its `inA` and `inB` inputs.


### ✅ Run It
And like magic Python can make a Niagara 4 .bog file is less than a blink of an eye.

```bash
python examples/write_adder.py
```

Then open `tight_layout_adder.bog` in Workbench to view and test the wire sheet logic.


![Adder Logic Created with Python](snips/addrMadeWithPy.jpg)


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

