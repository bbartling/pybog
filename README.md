# pybog: A Python Toolkit for Niagara BOG & DIST Files

`bog_builder` is a Python package for constructing Niagara Baja Object Graphs `.bog` files programmatically. The goal is for AI to assist human controls engineers in rapidly prototyping complex HVAC sequencing within wire sheet logic. If the software engineering community can prototype quickly, why shouldn’t the controls engineering community be able to do the same?

![Leave Temp Snip](https://github.com/bbartling/pybog/blob/develop/pybog_image.png)


## Local Python Project Setup
On WSL in the root directory afer after cloning project run:
>
> ```bash
> wsl
> pip install .
> ```
>

To uninstall bog_builer if developing
> ```bash
> pip uninstall bog_builder
> ```
>

Optinal run unit tests
> pytest


## Running Example Scripts with WSL

Each example script can be executed directly in **WSL (Windows Subsystem for Linux)** to generate a `.bog` file and drop it straight into your Niagara Workbench `JENEsys` directory. All example Python files are also compiled into a text file and used for LLM context.


1. **Run a specific example from project root directory**
   Pass the Niagara Workbench path as the output directory (`-o` argument):

   ```bash
   python examples/bool_latch_play_ground.py -o /mnt/c/Users/ben/Niagara4.11/JENEsys
   ```

   This will create:

   ```
   /mnt/c/Users/ben/Niagara4.11/JENEsys/bool_latch_play_ground.bog
   ```

2. **Open Workbench**
   Now you can import or open the generated `.bog` file inside your Niagara Workbench environment under the JENEsys station.

---

⚡ **Tip:**
If you don’t want to type `-o` every time, you can edit each example script and change the default in its argparse:

```python
parser.add_argument(
    "-o",
    "--output_dir",
    default="/mnt/c/Users/ben/Niagara4.11/JENEsys",
    help="Output directory for the .bog file."
)
```

Then you can just run:

```bash
python examples/bool_latch_play_ground.py
```

and it will always drop files directly into your Workbench directory for easy fast testing.

---

## Bog Builder Python API Example

This is a code snip from the `examples\subtract_simple.py` file with optional `start_sub_folder` folder structures.

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

bog_filename = f"{script_filename}.bog"
output_path = os.path.join(args.output_dir, bog_filename)
os.makedirs(args.output_dir, exist_ok=True)
builder.save(output_path)
print(f"\nSuccessfully created Niagara .bog file at: {output_path}")

```


When run, it will create a `.bog` file that can be directly imported into Workbench. Behind the scenes, `pybog` automatically arranges the grid layout to keep it neat and human-readable. Placing logic inside subfolders is optional, but it’s a great way to keep your bog files organized and clean. And yes—AI can handle all of this for you, too 😉.


```bash
python examples/subtract_simple.py -o /mnt/c/Users/ben/Niagara4.11/JENEsys
```

![subtract image](snips/simpleSubtract.png)


## Write Your Own `.bog` File in XML from scratch

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

### How it Works

* Each `<p>` tag represents a Niagara component or a **slot within a component** (like `out` or `fallback`). Each `<a>` tag represents an **action** on that component, like `set` or `override`.
* The `f` attribute (flags) is critical for controlling behavior. `f="s"` makes a slot **settable**, while `f="h"` or `f="ho"` **hides** a slot or action, which is how we create read-only points.
* To set a **default value**, the `out` and `fallback` slots must be fully defined as complex properties containing nested `<p n="value".../>` and `<p n="status".../>` tags.
* `h="1"`, `h="2"`, etc., are unique **handles** that links use to reference their source and target components.
* `wsAnnotation` controls the block's position on the wiresheet. The coordinates are calculated using our **Hierarchical Data Flow** strategy to ensure a clean, grid-based layout.
* The `Add` block's links use these handles to reference the `out` slots from `Input1` and `Input2` and connect them to its `inA` and `inB` inputs.


![Adder Logic Created with Python](https://github.com/bbartling/pybog/blob/develop/snips/addrMadeWithPy.jpg)


---


# 🔧 Using ChatGPT Agent Mode to Build `.bog` Files

The workflow is entirely conversational: upload your project zip, describe the control sequence you need, and ChatGPT will do the rest. Be se sure to hit the plus sign to enable "Agent" mode in ChatGPT.


![Agent mode snip](https://github.com/bbartling/pybog/blob/develop/snips/agent_mode_snip.png)

## 🚀 How It Works

1. **Upload the project zip**
   In the chat interface, attach the `pybog-develop.zip` file (found in this repository). The agent will automatically extract the archive and inspect the code.

2. **Describe your control logic**
   Tell ChatGPT what sequence of operations you want to implement. For example:

   > “Create a central plant with a boiler and chiller. Enable heating when the outside air temperature is 50 °F or below, and cooling when it is 65 °F or above. Use variable speed pumps with a differential pressure setpoint of 20 PSI and include a 2 °F deadband for both heating and cooling.”

3. **ChatGPT builds and tests the script**

   * The agent writes a Python script using the `BogFolderBuilder` API.
   * It runs the script in a sandboxed environment and inspects the results.
   * If it fails, the agent reads the traceback, fixes the code, and tries again.
   * This iterate-and-repair loop continues until a valid `.bog` file is produced.

4. **Download the result**
   Once successful, ChatGPT presents a link to download the generated `.bog` file. You can import this file directly into Niagara Workbench for testing.

---

## ✅ Advantages

* No API key required
* No local Python setup
* Faster prototyping directly within the conversation

---

## 📊 AI Agent

The following Mermaid diagram illustrates the high-level flow when using ChatGPT Agent Mode:

```mermaid
flowchart TD
  start([Start chat session]) --> upload[User uploads pybog zip]
  upload --> describe[User describes desired control logic]
  describe --> init[Agent extracts context files and builder]
  init --> iterate{{Is first attempt?}}

  iterate -- Yes --> gen[Agent generates Python script]
  iterate -- No  --> fix[Agent repairs script using previous code and traceback]

  gen --> write[Write script to sandbox]
  fix --> write

  write --> run[Execute script and build .bog]
  run --> success{Run ok and file created?}

  success -- Yes --> done[Present download link\nExit]
  success -- No  --> cap[Capture error/traceback]
  cap --> retry{Attempts < max allowed?}
  retry -- Yes --> incr[Update attempt count and context]
  incr --> iterate
  retry -- No --> fail[Report failure\nExit]
```

---

## 💡 Tips

* **Be specific** when describing your control logic (setpoints, deadbands, number of pumps, etc.). The more detail you provide, the more accurate the generated `.bog` file will be.
* **Validate in Workbench**: After downloading, import the `.bog` file into Niagara Workbench to review the wiresheet and adjust as needed.

With Agent Mode, you can rapidly prototype complex HVAC sequences without writing any code yourself. Just describe what you need, and let ChatGPT handle the heavy lifting.

---



### Generate Context Text Files

The **context directory** contains documentation specifically formatted for use by the LLM agent.
Running the generator will take all Python files in the `examples` directory and combine them into a set of **LLM-friendly documentation files** (see [GoFast MCP docs](https://gofastmcp.com/getting-started/welcome#llm-friendly-docs) for the format specification).

* **`llms.txt`** — a lightweight *sitemap* listing each example file and its relative path.
* **`llms-full.txt`** — a single, concatenated file with the complete source of every example, wrapped with clear delimiters (`=== FILE: ... ===`, `=== CODE START ===`, `=== CODE END ===`).
  ⚠️ *Note:* this file can be quite large and may exceed the context window of some LLMs. For this project the `llms-full.txt` can push upwords of 20,000 tokens.

Generate the docs with:

```bash
python src/bog_builder/generate_llm_docs.py --examples examples --output context
```

This ensures the agent has direct access to all available example scripts, either as a quick index (`llms.txt`) or full training context (`llms-full.txt`).

---

## Traversing Baja Object Graphs

Niagara represents the contents of a station as a directed graph of objects and properties.
When working with the raw XML stored inside `.bog` and `.dist` archives you are effectively traversing this graph.

The graph is **not strictly hierarchical**: components can have links and references to other components across folders, and cycles may exist in more complex projects.

### Best Practices

* **Parse once, traverse many.** Extract the `file.xml` contents into an `xml.etree.ElementTree` and hold onto the root element. Re-parsing repeatedly is expensive.
* **Use breadth-first or depth-first search with a visited set.** Each component element has a unique handle (`h` attribute). Track visited handles to avoid infinite loops.
* **Follow both containment and link relationships.** Components are nested via `<p h=...>` elements, but logical connections are represented with `b:Link` child elements.
* **Build a handle → name map.** Handles (e.g. `s="h:123"`) are common in link definitions. Build a dictionary so you can resolve these references.
* **Be mindful of palettes.** The `type` attribute encodes the palette and block name (e.g. `kitControl:Add`). Grouping by palette helps narrow searches or generate statistics.

### Analyzer Class

The `Analyzer` in `bog_builder.analyzer` encapsulates these patterns. It:

* Parses a `.bog` or `.dist` archive and extracts a **flat JSON structure** of components, properties, and links.
* Builds a **handle map** so you can resolve references by handle.
* Provides helpers to **count kitControl blocks** and generate bar/pie charts.

### Example Usage

Analyse a `.dist` file, export JSON, and produce charts:

```bash
python -m bog_builder.analyzer "/path/to/file.dist" \
  -o "/path/to/output.json" \
  --plots "/path/to/outputdir"
```

This will:

* Save the JSON analysis into `output.json`.
* Generate two PNGs in the `outputdir` folder:

  * `kitcontrol_counts_bar.png`
  * `kitcontrol_counts_pie.png`

---

## Example Output

**Bar Chart (counts by block type)**
![kitControl Bar](https://github.com/bbartling/pybog/blob/develop/snips/kitcontrol_counts_bar.png)

**Pie Chart (distribution of block usage)**
![kitControl Pie](https://github.com/bbartling/pybog/blob/develop/snips/kitcontrol_counts_pie.png)

---

👉 With this, you now have both **machine-readable JSON for reverse engineering** and **visual plots for quick insights** into station complexity and palette usage.

---

[🎥 Keep Up with Talk Shop With Ben on YouTube](https://www.youtube.com/@TalkShopWithBen)

---

## Component Library (kitControl)

Reference logic building blocks from Niagara’s kitControl palette are documented in `pdf/docKitControl.pdf`.

---

## License

MIT License — free for reuse with attribution. Pull requests welcome.

