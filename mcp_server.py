"""A lightweight MCP‑style server exposing the example builders as API endpoints.

This module uses FastAPI to provide a minimal HTTP interface for running
the bundled example scripts.  Each Python script in the ``examples``
directory is treated as a callable tool: the list of available
examples can be fetched via a ``GET`` request and individual examples
can be executed via ``POST``.  The executed script writes its
``.bog`` output into a user‑specified directory.

This server is a full implementation of the Model Context Protocol (MCP)
principles: exposing functions (examples) with well‑defined and discoverable
inputs and returning structured results.

To run the server locally:

.. code-block:: sh

   uvicorn mcp_server:app --reload

Once running, the available endpoints are:

* ``GET /examples`` – returns a list of available example tools, including their
  descriptions and input schemas.
* ``POST /examples/{example_name}`` – executes the named example,
  writing its output to a directory provided in the request body.
* ``GET /source-code`` – returns a detailed introspection of the bog_builder.builder module.
"""

from __future__ import annotations

import subprocess
import sys
import ast
import inspect
import types
from pathlib import Path
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

# Assuming bog_builder is installed and accessible
try:
    from bog_builder import builder
    from bog_builder.analyzer import Analyzer
except ImportError:
    print("Warning: bog_builder or its dependencies are not installed. Analyzer and source code introspection may fail.")
    builder = None
    Analyzer = None


BASE_DIR = Path(__file__).resolve().parent
EXAMPLES_DIR = BASE_DIR / "examples"


app = FastAPI(
    title="Bog Builder MCP Server",
    description="Expose example scripts as callable endpoints. This is a demonstration of the Model Context Protocol.",
    version="0.3.0",  # Version bumped to reflect new endpoint
)


# --- MCP Metadata Models ---


class ExampleParameter(BaseModel):
    """Schema for a single input parameter for an example script."""

    name: str = Field(description="The name of the parameter.")
    type: str = Field(description="The data type of the parameter (e.g., 'string').")
    description: str = Field(description="A brief description of the parameter.")
    required: bool = Field(description="Whether the parameter is required.")


class ExampleDetails(BaseModel):
    """Schema describing a single, callable example tool."""

    name: str = Field(description="The unique name of the example, used for execution.")
    description: Optional[str] = Field(
        description="Detailed explanation of what the example does."
    )
    inputs: List[ExampleParameter] = Field(
        description="A list of input parameters the example requires."
    )


# --- Original Request/Response Models ---


class RunExampleRequest(BaseModel):
    """Schema for requests to run an example."""

    output_dir: Optional[str] = None


class AnalyzeRequest(BaseModel):
    """Schema for analysis requests."""

    file_path: str
    plots_dir: Optional[str] = None


# --- Helper functions ---


def get_example_details(script_path: Path) -> ExampleDetails:
    """
    Parses a Python script file to extract its metadata using AST.
    This allows us to inspect the script without executing it.
    """
    try:
        source = script_path.read_text()
        tree = ast.parse(source)
        docstring = ast.get_docstring(tree)
    except Exception:
        docstring = "Could not parse docstring."

    inputs = [
        ExampleParameter(
            name="output_dir",
            type="string",
            description="Path (absolute or relative) where the output .bog file will be written.",
            required=False,
        )
    ]

    return ExampleDetails(name=script_path.name, description=docstring, inputs=inputs)

# NEW: This function encapsulates your provided introspection script.
def inspect_source_code(mod) -> Dict[str, Any]:
    """
    Performs introspection on a given module and returns a structured dictionary.
    """
    if mod is None:
        return {"error": "Module not loaded"}
    
    try:
        mod_file = inspect.getsourcefile(mod) or inspect.getfile(mod)
    except TypeError:
        mod_file = None

    def is_defined_here(obj):
        try:
            f = inspect.getsourcefile(obj) or inspect.getfile(obj)
            return mod_file is not None and f == mod_file
        except (TypeError, OSError):
            return False

    result = {
        "module_name": mod.__name__,
        "file_path": mod_file,
        "classes": [],
        "functions": [],
        "constants": [],
    }

    # Introspect classes
    classes = [(n, c) for n, c in inspect.getmembers(mod, inspect.isclass) if is_defined_here(c)]
    for name, cls in classes:
        bases = [b.__name__ for b in cls.__bases__ if b is not object]
        class_details = {
            "name": name,
            "bases": bases,
            "methods": [],
            "properties": [],
        }
        for attr_name, attr_val in cls.__dict__.items():
            if attr_name.startswith("__") and attr_name.endswith("__"):
                continue
            if isinstance(attr_val, (types.FunctionType, types.BuiltinFunctionType, staticmethod, classmethod)):
                class_details["methods"].append(attr_name)
            elif isinstance(attr_val, property):
                class_details["properties"].append(attr_name)
        result["classes"].append(class_details)

    # Introspect functions
    funcs = [(n, f) for n, f in inspect.getmembers(mod, inspect.isfunction) if is_defined_here(f)]
    for name, fn in funcs:
        result["functions"].append({"name": name, "signature": str(inspect.signature(fn))})
        
    # Introspect constants
    for n, v in vars(mod).items():
        if n.isupper() and (is_defined_here(v) or not callable(v)):
            result["constants"].append(n)
            
    return result

# --- API Endpoints ---


@app.get("/examples", response_model=List[ExampleDetails])
async def list_examples() -> List[ExampleDetails]:
    """
    Return a detailed list of all available example scripts, including
    their descriptions and input schemas. This is the core of MCP.
    """
    if not EXAMPLES_DIR.is_dir():
        raise HTTPException(
            status_code=500, detail=f"Examples directory not found: {EXAMPLES_DIR}"
        )

    scripts = sorted(f for f in EXAMPLES_DIR.glob("*.py") if not f.name.startswith("."))
    return [get_example_details(script) for script in scripts]


# NEW: Endpoint to expose the source code introspection.
@app.get("/source-code")
async def get_source_code() -> dict:
    """
    Returns a detailed, structured introspection of the `bog_builder.builder` module,
    revealing its classes, methods, and functions.
    """
    if builder is None:
        raise HTTPException(status_code=500, detail="bog_builder.builder module could not be imported.")
    
    try:
        return inspect_source_code(builder)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to inspect source code: {e}")


@app.post("/examples/{example_name}")
async def run_example(example_name: str, req: RunExampleRequest) -> dict:
    """Execute the specified example script."""
    example_path = EXAMPLES_DIR / example_name
    if not example_path.is_file():
        raise HTTPException(
            status_code=404, detail=f"Example not found: {example_name}"
        )

    if req.output_dir:
        output_dir = Path(req.output_dir).expanduser()
    else:
        output_dir = BASE_DIR / "generated"
    output_dir.mkdir(parents=True, exist_ok=True)

    command = [sys.executable, str(example_path), "-o", str(output_dir)]

    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        raise HTTPException(status_code=500, detail=f"Execution failed: {exc.stderr}")

    return {
        "status": "ok",
        "output_dir": str(output_dir),
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


@app.post("/analyze")
async def analyze_station(req: AnalyzeRequest) -> dict:
    """Analyze a Niagara archive and optionally generate kitControl charts."""
    if Analyzer is None:
        raise HTTPException(
            status_code=500,
            detail="Analyzer module is not available in this environment",
        )
    file_path = Path(req.file_path)
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
    try:
        analyzer = Analyzer(str(file_path))
        counts = analyzer.count_kitcontrol_components()
        response: dict = {"counts": counts}
        if req.plots_dir:
            try:
                plots = analyzer.plot_kitcontrol_counts(req.plots_dir)
                response["plots"] = plots
            except Exception as exc:
                response["plot_error"] = str(exc)
        return response
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))