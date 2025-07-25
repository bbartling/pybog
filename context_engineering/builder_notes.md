Sure! Here's your content reformatted as a professional `README.md` for a GitHub project, complete with structured sections and collapsible `<details>` tags for the developer guide and example:

---

````markdown
# 🧠 pybog - Niagara Wiresheet Layout & .bog File Generator

`pybog` is a Python toolkit that enables automated generation of Tridium Niagara `.bog` files using a clean, grid-based layout strategy inspired by human design logic. This repository outlines the **layout philosophy** and provides a **developer API** to build control logic programmatically.

---

## 📐 Wiresheet Layout Strategy: Hierarchical Data Flow

### 🎯 Primary Goal

To arrange components in a **clean, left-to-right data flow** that mimics how a human would build Niagara logic. Inputs appear on the left and flow through logic blocks to outputs on the right, using consistent grid alignment.

---

### 🧱 Core Concepts

- **Columns:** Logical vertical bands for Inputs → Logic → Outputs.
- **Data Flow:** Follows component links to determine placement.
- **Typewriter Wrapping:** New rows begin when right-hand canvas limit is reached, preventing horizontal scrolling.

---

### 📏 Layout Parameters

| Parameter        | Value        | Description                                       |
|------------------|--------------|---------------------------------------------------|
| `x_increment`     | `10`         | Horizontal grid unit                              |
| `y_increment`     | `10`         | Vertical grid unit                                |
| `x_column_width`  | `150`        | Distance between columns                          |
| `max_x`           | `592`        | Canvas wrap limit on X-axis                       |
| `start_x`         | `10`         | Starting X coordinate for all rows                |
| `start_y`         | `10`         | Starting Y coordinate for layout                  |

---

### 🤖 Placement Algorithm

- **Level Assignment:**
  - Components with no inputs = **Level 0 (Inputs)** → 1st column.
  - Logic that depends on Level 0 = **Level 1**, and so on.

- **Multi-Input Alignment:**
  - When a component has multiple inputs, sources are vertically stacked.
  - Target is placed to the right, vertically centered to its inputs.

- **Typewriter Wrapping:**
  - If `x + x_column_width > max_x`:
    - Move to new row: `y = row_max_y + y_increment`, `x = start_x`.

---

<details>
<summary>🛠️ Developer Guide: Generating Niagara BOG Files with <code>pybog</code></summary>

### 📌 Objective

Translate human-readable control logic into executable `.bog` files using Python.

---

### ⚙️ Generation Workflow

1. **Deconstruct Request**
   - Identify components (e.g., `Add`, `Tstat`, `Writable`).
   - Map their links and properties (e.g., default values, read-only flags).

2. **Map to API**
   - Use `BogFolderBuilder` to add components and links.
   - Assign `ws_annotation` to control layout (manual override required).

3. **Output `.bog`**
   - Save the file using `builder.save(file_path)`.

---

### 📚 BogFolderBuilder API Reference

```python
BogFolderBuilder(folder_name)
````

* Initializes the wiresheet.

```python
add_numeric_writable(name, default_value=0.0, read_only=False, ws_annotation=None)
```

* Add a `control:NumericWritable`.

```python
add_component(comp_type, name, properties=None, actions=None, ws_annotation=None)
```

* Add a general Niagara component.

```python
add_link(source_comp, source_slot, target_comp, target_slot)
```

* Define signal flow between components.

```python
save(file_path)
```

* Export `.bog` file to disk.

---

### 🧪 Example: Building "Adder" Logic

**User Prompt:**

> "Create a simple wiresheet that adds two numbers together. I need two inputs with default values of 6 and 4, and an output that shows the sum. The output should be read-only."

**Python Script:**

```python
# build_adder_logic.py
import sys, os, argparse
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.bog_builder import BogFolderBuilder

def main():
    parser = argparse.ArgumentParser(description="Build the Adder Logic .bog file.")
    parser.add_argument("-o", "--output_dir", default=".", help="Output directory for the .bog file.")
    args = parser.parse_args()

    builder = BogFolderBuilder("MyAdderLogic")

    # --- Column 1: Inputs (x=20) ---
    builder.add_numeric_writable(name="Input1", default_value=6.0, ws_annotation="20,20,8")
    builder.add_numeric_writable(name="Input2", default_value=4.0, ws_annotation="20,100,8")

    # --- Column 2: Logic (x=180) ---
    builder.add_component(comp_type="kitControl:Add", name="Add", ws_annotation="180,60,8")

    # --- Column 3: Output (x=340) ---
    builder.add_numeric_writable(name="Sum", read_only=True, ws_annotation="340,60,8")

    # --- Define Links ---
    builder.add_link("Input1", "out", "Add", "inA")
    builder.add_link("Input2", "out", "Add", "inB")
    builder.add_link("Add", "out", "Sum", "in16")

    # --- Save the File ---
    output_path = os.path.join(args.output_dir, "adder_logic.bog")
    os.makedirs(args.output_dir, exist_ok=True)
    builder.save(output_path)

if __name__ == "__main__":
    main()
```

</details>

---

## 🔗 Repository Structure

```
pybog/
├── src/
│   └── bog_builder.py      # Main API class
├── examples/
│   └── build_adder_logic.py
├── README.md
└── .bog/                   # Output directory for generated .bog files
```

---

## 📎 License

MIT License © 2025

---

## ✨ Author

Ben Bartling
HVAC Controls + AI Optimization Enthusiast
[https://github.com/bbartling](https://github.com/bbartling)

```

---

Let me know if you'd like it turned into a live `README.md` file or bundled into a GitHub repo template.
```
