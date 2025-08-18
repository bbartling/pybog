# pybog: A Python Toolkit for Niagara BOG & DIST Files

`bog_builder` is a Python package for constructing Niagara `.bog` files programmatically.

![Leave Temp Snip](https://github.com/bbartling/pybog/blob/develop/pybog_image.png)

It exposes a `BogFolderBuilder` class which lets you assemble logic blocks, group them
into sub‑folders, link them together, and save the result as a `.bog` archive.  All
user input is validated via [Pydantic](https://docs.pydantic.dev/), so invalid names,
component types or link definitions produce clear error messages rather than mysterious
failures at runtime.  Time‑based properties such as delays and periods accept both
millisecond strings and human‑friendly formats like ``"1s"`` or ``"1m"``.

The repository follows a standard PyPI layout using a top‑level ``src/`` directory for
the package code and a ``tests/`` folder containing functional examples.  The tests
demonstrate how to use the builder API to reproduce a variety of Niagara Workbench
programs—including average/min/max calculators, Boolean latches, ping‑pong counters and
top‑N selection algorithms.  To run the tests, install the package in editable mode
and invoke ``pytest``:

```sh
pip install -e .
pytest
```

If you wish to see how specific Workbench examples are recreated programmatically,
inspect the files under ``tests/test_more_examples.py`` and ``tests/test_workbench_examples.py``.
Each test constructs a graph matching the corresponding script found at the root of
this repository (e.g. ``manual_average_min_max.py``, ``ping_pong_counter.py``) and asserts
that the resulting `.bog` file is created successfully.

> **Note**
>
> The tests expect the ``bog_builder`` package to be importable.  When running
> tests without first installing the package, a ``conftest.py`` in the ``tests``
> directory automatically adds the project’s ``src`` folder to ``sys.path`` so
> that imports resolve correctly.  Alternatively, you can install the package
> in editable mode prior to running the tests:
>
> ```sh
> pip install -e .
> pytest
> ```
>

> **Note to uninstall bog_builer**
> from within your virtual environment or wherever you installed it
> ```sh
> pip uninstall bog_builder
> ```
>

## Building a simple thermostat

The ``BogFolderBuilder`` can be used to assemble more complex control logic.  As an
illustrative example, here’s how you might build a simple thermostat with heating,
cooling and fan commands.  The thermostat exposes numeric and boolean writables for
the current space temperature, setpoints, hysteresis, mode and fan‐auto selection, and
produces outputs for each command:

- ``SpaceTemp`` – current space temperature (numeric)
- ``HeatSP`` – heating setpoint (numeric)
- ``CoolSP`` – cooling setpoint (numeric)
- ``Hysteresis`` – deadband around the setpoints (numeric)
- ``Mode`` – 0=Off, 1=Heat, 2=Cool (numeric)
- ``FanAuto`` – if ``False`` then the fan runs whenever either Heat or Cool is active (boolean)
- ``Output_HeatCmd`` – command to enable heating (boolean)
- ``Output_CoolCmd`` – command to enable cooling (boolean)
- ``Output_FanCmd`` – command to enable the fan (boolean)

The logic is as follows:

* When ``Mode == 1`` (heat) **and** ``SpaceTemp < HeatSP − Hysteresis`` then ``HeatCmd`` is ``True``.
* When ``Mode == 2`` (cool) **and** ``SpaceTemp > CoolSP + Hysteresis`` then ``CoolCmd`` is ``True``.
* The fan command is ``True`` whenever either ``HeatCmd`` or ``CoolCmd`` is ``True``.  If ``FanAuto``
  is ``False`` the fan runs regardless of the heating/cooling state.

Here’s a complete example using the builder API to create this thermostat and
write it to a ``.bog`` file:

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

```sh
python build_thermostat.py -o "C:\Users\ben\Niagara4.11\JENEsys"
```

This will create ``Thermostat.bog`` in the specified folder.  You can then import
and test it within Niagara Workbench.

## Creating a hot water reset block

Linear reset blocks are another common pattern in Niagara programming.  A reset
performs a linear interpolation between two pairs of limits.  For example,
you might want to reset a hot water supply temperature setpoint based on
outdoor air temperature.  The `Reset` component takes five inputs:

* ``inA`` – the current process value (e.g. outdoor air temperature).
* ``inputLowLimit`` and ``inputHighLimit`` – the range of the process value.
* ``outputLowLimit`` and ``outputHighLimit`` – the corresponding range of the output.

The output value is interpolated between ``outputLowLimit`` and
``outputHighLimit`` depending on where ``inA`` sits between the input limits.

The package ships with an example script `examples/hot_water_reset_example.py` that
constructs a hot water reset.  The script defines numeric writables for the
process value and its limits, instantiates a `kitControl:Reset` block with
matching fallback values, wires up the inputs and output, and saves the
resulting `.bog` file.  The generated XML mirrors the structure exported by
Workbench, including nested `Link` elements under the target components and
status slots on the `Reset` block.

Run the example like so:

```sh
python examples/hot_water_reset_example.py -o "C:\Users\ben\Niagara4.11\JENEsys"
```

This creates ``HotWaterTempReset.bog`` in your chosen directory, ready for
import into Workbench.  You can modify the limit values in the script to suit
your application or use it as a template for chilled water resets.


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

## LLM‑friendly documentation and MCP server

As your collection of example scripts grows it becomes challenging for
a large language model (LLM) to discover all of the available usage
patterns without reading each file individually.  To make this easier
the package includes a utility for generating LLM‑friendly
documentation.  The ``scripts/generate_llm_docs.py`` script walks the
``examples`` directory and writes two files into a specified output
directory:

* **llms.txt** – a simple sitemap listing each example file name
  along with its relative directory.  This file can be used by
  automation to locate individual examples.
* **llms-full.txt** – the full source code of every example with
  clear delimiters.  Each section begins with ``=== FILE: ... ===``
  followed by the directory, the code contents, and an ``=== CODE END ===``
  marker.  These files can be consumed directly by LLMs to provide
  them with concrete examples of using the builder API.

To generate the documentation, run the following from the root of
the repository:

```sh
python scripts/generate_llm_docs.py --examples examples --output context
```

This command will create a ``context`` folder (if it does not
already exist) and populate it with ``llms.txt`` and ``llms-full.txt``.

In addition to the documentation generator, the repository contains
``mcp_server.py``, a lightweight HTTP service powered by
[FastAPI](https://fastapi.tiangolo.com/).  While not a complete
implementation of the Model Context Protocol, it demonstrates how to
expose your example scripts as callable endpoints – much like the
``@tool`` decorator in FastMCP.  You can run the service locally
with:

```sh
uvicorn bog_pkg_mod.mcp_server:app --reload
```

Once running, a ``GET`` request to ``/examples`` returns the list of
available example scripts.  A ``POST`` request to
``/examples/{example_name}`` with an optional JSON body containing an
``output_dir`` will execute the named script and write its `.bog`
output to the specified directory.  The response includes the
standard output and error streams so you can inspect any issues.

## Traversing Baja Object Graphs

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

```sh
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

