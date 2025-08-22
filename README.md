# pybog: A Python Toolkit for Niagara BOG & DIST Files

`bog_builder` is a Python package for constructing Niagara Baja Object Graphs `.bog` files programmatically.

![Leave Temp Snip](https://github.com/bbartling/pybog/blob/develop/pybog_image.png)


## Local Python Project Setup
On WSL in the root directory afer after cloning project run:
>
> ```bash
> pip install -e .
> pytest
> ```
>

To uninstall bog_builer
> ```bash
> pip uninstall bog_builder
> ```
>

## Building a simple thermostat


Here’s a complete example using the builder API to create this thermostat and write it to a ``.bog`` file which can then be imported to JACE via the Workbench tool:

```python
from bog_builder import BogFolderBuilder

builder = BogFolderBuilder("Thermostat")

# Define inputs
builder.add_numeric_writable("SpaceTemp", default_value=72.0)
builder.add_numeric_writable("HeatSP", default_value=68.0)
builder.add_numeric_writable("CoolSP", default_value=74.0)
builder.add_numeric_writable("Hysteresis", default_value=1.0)
builder.add_numeric_writable("Mode", default_value=0.0)  # 0=Off, 1=Heat, 2=Cool
builder.add_boolean_writable("FanAuto", default_value=True)

# Define outputs
builder.add_boolean_writable("Output_HeatCmd")
builder.add_boolean_writable("Output_CoolCmd")
builder.add_boolean_writable("Output_FanCmd")

# Constants for comparing the mode value
builder.add_component("kitControl:NumericConst", "Const1", properties={"value": 1})
builder.add_component("kitControl:NumericConst", "Const2", properties={"value": 2})

# Blocks to detect heating/cooling modes
builder.add_component("kitControl:GreaterThanEqual", "Mode_GE_1")
builder.add_component("kitControl:LessThanEqual", "Mode_LE_1")
builder.add_component("kitControl:And", "IsHeatMode")

builder.add_component("kitControl:GreaterThanEqual", "Mode_GE_2")
builder.add_component("kitControl:LessThanEqual", "Mode_LE_2")
builder.add_component("kitControl:And", "IsCoolMode")

# Compute ``SpaceTemp + Hysteresis`` and ``CoolSP + Hysteresis``
builder.add_component("kitControl:Add", "SpacePlusHyst")
builder.add_component("kitControl:Add", "CoolSP_plus_Hyst")

# Comparisons against setpoints
builder.add_component("kitControl:LessThanEqual", "IsBelowHeat")
builder.add_component("kitControl:GreaterThanEqual", "IsAboveCool")

# Gates and logic combining blocks
builder.add_component("kitControl:And", "HeatCmdGate")
builder.add_component("kitControl:And", "CoolCmdGate")
builder.add_component("kitControl:Or", "HeatOrCool")
builder.add_component("kitControl:Not", "FanAutoNot")
builder.add_component("kitControl:Or", "FanCmdGate")

# Wiring for mode comparisons (Mode == 1)
builder.add_link("Mode", "out", "Mode_GE_1", "inA")
builder.add_link("Const1", "out", "Mode_GE_1", "inB")
builder.add_link("Mode", "out", "Mode_LE_1", "inA")
builder.add_link("Const1", "out", "Mode_LE_1", "inB")
builder.add_link("Mode_GE_1", "out", "IsHeatMode", "inA")
builder.add_link("Mode_LE_1", "out", "IsHeatMode", "inB")

# Wiring for mode comparisons (Mode == 2)
builder.add_link("Mode", "out", "Mode_GE_2", "inA")
builder.add_link("Const2", "out", "Mode_GE_2", "inB")
builder.add_link("Mode", "out", "Mode_LE_2", "inA")
builder.add_link("Const2", "out", "Mode_LE_2", "inB")
builder.add_link("Mode_GE_2", "out", "IsCoolMode", "inA")
builder.add_link("Mode_LE_2", "out", "IsCoolMode", "inB")

# Sum the hysteresis with the space and cooling setpoints
builder.add_link("SpaceTemp", "out", "SpacePlusHyst", "inA")
builder.add_link("Hysteresis", "out", "SpacePlusHyst", "inB")
builder.add_link("CoolSP", "out", "CoolSP_plus_Hyst", "inA")
builder.add_link("Hysteresis", "out", "CoolSP_plus_Hyst", "inB")

# Compare ``SpaceTemp + Hyst <= HeatSP``  (heat threshold)
builder.add_link("SpacePlusHyst", "out", "IsBelowHeat", "inA")
builder.add_link("HeatSP", "out", "IsBelowHeat", "inB")

# Compare ``SpaceTemp >= CoolSP + Hyst`` (cool threshold)
builder.add_link("SpaceTemp", "out", "IsAboveCool", "inA")
builder.add_link("CoolSP_plus_Hyst", "out", "IsAboveCool", "inB")

# Combine heat mode and threshold
builder.add_link("IsHeatMode", "out", "HeatCmdGate", "inA")
builder.add_link("IsBelowHeat", "out", "HeatCmdGate", "inB")

# Combine cool mode and threshold
builder.add_link("IsCoolMode", "out", "CoolCmdGate", "inA")
builder.add_link("IsAboveCool", "out", "CoolCmdGate", "inB")

# OR heat and cool commands for fan logic
builder.add_link("HeatCmdGate", "out", "HeatOrCool", "inA")
builder.add_link("CoolCmdGate", "out", "HeatOrCool", "inB")

# Invert FanAuto to produce a manual fan override
builder.add_link("FanAuto", "out", "FanAutoNot", "in")

# Combine heat/cool or manual override for the fan command
builder.add_link("HeatOrCool", "out", "FanCmdGate", "inA")
builder.add_link("FanAutoNot", "out", "FanCmdGate", "inB")

# Wire the gates to the final outputs
builder.add_link("HeatCmdGate", "out", "Output_HeatCmd", "in16")
builder.add_link("CoolCmdGate", "out", "Output_CoolCmd", "in16")
builder.add_link("FanCmdGate", "out", "Output_FanCmd", "in16")

# Save the `.bog` archive.  On Windows you can direct this to your Workbench
# user directory by passing an absolute path, e.g. ``"C:\\Users\\ben\\Niagara4.11\\JENEsys\\Thermostat.bog"``.
builder.save("Thermostat.bog")
```

To place the resulting ``.bog`` file directly into your Niagara workbench user
directory, pass the desired output path to the ``save`` method (or to your own
script via a command‑line ``-o`` flag) and ensure the directory exists.  For example on
Windows:

```bash
python build_thermostat.py -o "C:\Users\ben\Niagara4.11\JENEsys"
```

This will create ``Thermostat.bog`` in the specified folder.  You can then import
and test it within Niagara Workbench.


## 👷 Write Your Own `.bog` File in XML from scratch

The Python script operates by creating the entire XML structure of the Niagara .bog file as a single, multi-line text string. This string contains all the necessary tags to define each component, its properties, and the links between them. Finally, the script writes this complete XML string directly into a new file, which Niagara can then open and display as a standard wiresheet.

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


![Adder Logic Created with Python](snips/addrMadeWithPy.jpg)


---

## LLM Agent - `generic_agent.py`

🚀 Experimental Iterative **BOG File Builder**!
Tested on **WSL** 🐧  
Powered by a **FREE API Key** from [Google AI Studio](https://aistudio.google.com/apikey) 🔑  
Running with **Gemini-2.5 Flash** ⚡

```bash
export GOOGLE_API_KEY='PASTE IT IN HERE!'
```

The `generic_agent.py` script lets you describe an HVAC control sequence in plain English and iteratively synthesizes a runnable Python builder script that creates a Niagara `.bog` file.  

It works like this:

1. **Prompt for description**  
   You’ll be asked to describe the control system logic you want (e.g. *"Create a central plant with heating and cooling setpoints of 40°F/45°F and 75°F/70°F with a free cooling range between 50 and 60°F"*).

2. **Prompt for bog file name**  
   You’ll also be asked to give a short, human-friendly name for the output file (e.g. *"central_plant_sequencing"*).  
   The agent forces the generated script to save exactly to that file, e.g.:  
   `/mnt/c/Users/ben/Niagara4.11/JENEsys/central_plant_sequencing.bog`

3. **Synthesize → Run → Fix loop**  
   - Attempt 1: the LLM generates a Python script into `.agent_tmp/` and runs it.  
   - If it fails, the agent captures the full traceback and sends both the failing code and the error back to the LLM.  
   - The LLM then repairs the script and tries again.  
   - This repeats up to `--max-iters` times (default 4).  

4. **Result**  
   Once successful, you’ll see debug logs from `BogFolderBuilder` and a success message where then you can open it right up in Workbench:  

```

✅ Generated .bog file at: /mnt/c/Users/ben/Niagara4.11/JENEsys/central\_plant\_sequencing.bog

```

5. **Stats**  
At the end, the script prints how many Gemini API calls were used and how many attempts were needed.  

Example:

```

—— Stats ——
Gemini calls: 2
Attempts: 2

```

---

### Command-line arguments

```bash
python generic_agent.py [--output <path>] [--max-iters N] [--workdir <dir>]
```

* `--output`: optional final destination for the `.bog`. If omitted, the file stays in the default Niagara output dir (`Niagara4.11/JENEsys`).
* `--max-iters`: max number of generate→run→fix attempts (default 4).
* `--workdir`: scratch directory for synthesized Python scripts (default `.agent_tmp/`).
  You should add `.agent_tmp/` to `.gitignore` since it only contains temporary generated scripts.

---

## Traversing Baja Object Graphs

TODO RESEARCH:

Niagara represents the contents of a station as a directed graph of
objects and properties.  When working with the raw XML stored inside
``.bog`` and ``.dist`` archives you are effectively traversing this
graph.  The graph is not strictly hierarchical: components can have
links and references to other components across folders, and cycles
may exist in more complex projects.  The following best practices
apply when traversing Baja object graphs programmatically:

* **Parse once, traverse many.**  Extract the ``file.xml`` contents
  into an ``xml.etree.ElementTree`` and hold onto the root element.
  Re‑parsing the XML repeatedly is expensive.
* **Use breadth‑first or depth‑first search with a visited set.**
  Each component element has a unique handle (the ``h`` attribute).
  Keep a set of visited handles to avoid infinite loops when
  following links and references.
* **Follow both containment and link relationships.**  Components are
  nested via ``<p h=...>`` elements, but logical connections are
  represented via ``b:Link`` child elements.  To reconstruct the
  full dependency graph you must consider both.
* **Build a handle→name map.**  It is common to refer to components
  by their handle in link definitions (e.g. ``s="h:123"``).  Create
  a dictionary mapping ``h:<handle>`` strings to component names so
  you can resolve these references during traversal.
* **Be mindful of palettes.**  The ``type`` attribute on each
  component encodes the palette and the block name (e.g.
  ``kitControl:Add``).  Grouping components by palette can help
  narrow your search or generate statistics.

The ``Analyzer`` class in ``bog_builder.analyzer`` encapsulates these
patterns.  It parses a station or BOG file, extracts a flat list of
components along with their properties and links, and can build a
handle map for you.  Beyond basic analysis, it includes helpers to
count how many ``kitControl`` components of each type are used and
generate visualisations of this data.  For example, to analyse a
``.dist`` file and produce bar and pie charts summarising the
kitControl blocks it contains:

```bash
python -m bog_builder.analyzer path/to/station.dist --count --plots analysis/plots
```

This command writes JSON analysis to stdout, prints a sorted list of
kitControl counts, and saves two images into ``analysis/plots``: one
bar chart and one pie chart.  These charts can provide insight into
which Niagara control blocks are most common in a given station.

---

[🎥 Keep Up with Talk Shop With Ben on YouTube](https://www.youtube.com/@TalkShopWithBen)

---

## 🧱 Component Library (kitControl)

Reference logic building blocks from Niagara’s kitControl palette are documented in `pdf/docKitControl.pdf`.

---

## 📄 License

MIT License — free for reuse with attribution.

