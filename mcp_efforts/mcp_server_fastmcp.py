# mcp_server_fastmcp.py
from __future__ import annotations

import importlib.util
import subprocess
import sys, os
import re
import ast
import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from io import StringIO
from contextlib import redirect_stdout, redirect_stderr
from uuid import uuid4

from fastmcp import FastMCP
from pydantic import BaseModel, Field

# Assume bog_builder is available in the environment
# We will mock the save method to capture output instead of writing a file.
try:
    from bog_builder import BogFolderBuilder
except ImportError:
    print("Warning: BogFolderBuilder not found. Using a mock class for demonstration.")

    # Define a mock if the real one isn't available for standalone testing
    class BogFolderBuilder:
        def __init__(self, folder_name: str, debug: bool = True):
            self._folder_name = folder_name
            self._content = f"<bog folder='{folder_name}'>...</bog>"

        def to_xml_string(self) -> str:
            # In a real scenario, this would generate the full BOG XML content.
            print(f"Serializing BOG data for '{self._folder_name}'")
            return self._content

        def save(self, path: str):
            # This method will be overridden/patched to prevent file writing.
            raise NotImplementedError("File saving is disabled on the MCP server.")


# Analyzer is optional; guard import
try:
    from bog_builder import Analyzer
except Exception:
    Analyzer = None

BASE_DIR = Path(__file__).resolve().parent
EXAMPLES_DIR = BASE_DIR / "examples"
GENERATED_DIR = BASE_DIR / "generated"
GENERATED_DIR.mkdir(exist_ok=True)

SAFE_NAME_RE = re.compile(r"^[A-Za-z0-9_\-\.]{1,80}$")

# MCP instance
mcp = FastMCP(name="Bog Builder MCP Server")


# ---- Models ----
class ExampleParameter(BaseModel):
    name: str = Field(description="The name of the parameter.")
    type: str = Field(description="The data type of the parameter (e.g., 'string').")
    description: str = Field(description="A brief description of the parameter.")
    required: bool = Field(description="Whether the parameter is required.")


class ExampleDetails(BaseModel):
    name: str = Field(description="The unique name of the example, used for execution.")
    description: Optional[str] = Field(
        description="Detailed explanation of what the example does."
    )
    inputs: List[ExampleParameter] = Field(
        description="A list of input parameters the example requires."
    )


class AnalyzeRequest(BaseModel):
    file_path: str
    plots_dir: Optional[str] = None


class SourceCode(BaseModel):
    name: str
    source: str


# ---- Helpers ----
def get_example_details(script_path: Path) -> ExampleDetails:
    try:
        source = script_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        docstring = ast.get_docstring(tree)
    except Exception:
        docstring = "Could not parse docstring."
    inputs = [
        ExampleParameter(
            name="output_dir",
            type="string",
            description="Path (absolute or relative) where the output .bog file will be written.",
            required=True,
        )
    ]
    return ExampleDetails(name=script_path.name, description=docstring, inputs=inputs)


# ---- Tools ----
@mcp.tool(
    name="list_examples",
    description="Return a detailed list of all available example scripts, including their descriptions and input schemas.",
)
async def list_examples() -> List[ExampleDetails]:
    if not EXAMPLES_DIR.is_dir():
        raise FileNotFoundError(f"Examples directory not found: {EXAMPLES_DIR}")
    scripts = sorted(f for f in EXAMPLES_DIR.glob("*.py") if not f.name.startswith("."))
    return [get_example_details(script) for script in scripts]


@mcp.tool(
    name="get_example_source",
    description="Returns the raw Python source of a specific example so LLMs can ingest code.",
)
async def get_example_source(example_name: str) -> SourceCode:
    example_path = EXAMPLES_DIR / example_name
    if not example_path.is_file():
        raise FileNotFoundError(f"Example not found: {example_name}")
    source_text = example_path.read_text(encoding="utf-8")
    return SourceCode(name=example_name, source=source_text)


@mcp.tool(
    name="get_example_sources",
    description="Return sources for multiple example scripts in one call.",
)
async def get_example_sources(example_names: List[str]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for name in example_names:
        p = EXAMPLES_DIR / name
        if p.is_file():
            out.append({"name": name, "source": p.read_text(encoding="utf-8")})
    return out


@mcp.tool(
    name="run_generated_script",
    description="Executes generated Python code in memory. The code must define a `build()` function that returns the BOG data as an XML string.",
)
async def run_generated_script(filename: str, source_code: str) -> Dict[str, Any]:
    """
    Executes the provided script in-process.
    The script is expected to define a function: `build() -> str`.
    This function should use the BogFolderBuilder and return the result of `builder.to_xml_string()`.
    This tool captures and returns the string data, stdout, and stderr. It does NOT save files.
    """
    if not SAFE_NAME_RE.match(filename) or not filename.endswith(".py"):
        raise ValueError("Invalid filename. Must be a .py file with a safe name.")

    # Write code to a temporary file in the 'generated' directory for importing.
    script_path = (GENERATED_DIR / filename).resolve()
    script_path.write_text(source_code, encoding="utf-8")

    # Ensure project directories are importable for dependencies like BogFolderBuilder.
    for p in {str(BASE_DIR), str(GENERATED_DIR)}:
        if p not in sys.path:
            sys.path.insert(0, p)

    buf_out, buf_err = StringIO(), StringIO()
    try:
        # Use a unique module name to avoid caching issues between runs.
        module_name = f"generated_mod_{uuid4().hex}"
        spec = importlib.util.spec_from_file_location(module_name, str(script_path))
        if not spec or not spec.loader:
            raise ImportError(f"Could not create module spec for {script_path}")

        mod = importlib.util.module_from_spec(spec)
        sys.modules[mod.__name__] = mod

        # Execute the module's code within a context that captures stdout/stderr.
        with redirect_stdout(buf_out), redirect_stderr(buf_err):
            spec.loader.exec_module(mod)
            build_func = getattr(mod, "build", None)

            if not callable(build_func):
                raise AttributeError(
                    "The script must define a callable function 'build()'."
                )

            # Call the build function and capture its return value.
            bog_data = build_func()

            if not isinstance(bog_data, str) or not bog_data.strip():
                raise TypeError(
                    "The 'build()' function must return a non-empty string of BOG XML data."
                )

        # If everything succeeded, return the captured data.
        return {
            "status": "ok",
            "bog_data": bog_data,
            "stdout": buf_out.getvalue()[-4000:],
            "stderr": buf_err.getvalue()[-4000:],
        }

    except Exception as e:
        # If any part of the execution fails, return a detailed error.
        # This removes the need for fallbacks and exposes errors directly.
        return {
            "status": "error",
            "error": f"{type(e).__name__}: {e}",
            "stdout": buf_out.getvalue()[-4000:],
            "stderr": buf_err.getvalue()[-4000:],
        }
    finally:
        # Clean up the generated file.
        if script_path.exists():
            script_path.unlink()


# ---- Resource (identifier for MCP clients; not an HTTP route) ----
@mcp.resource(
    uri="mcp://bog-builder/builder-api.json",
    description="Static API summary for the BogFolderBuilder, tailored for agents.",
    mime_type="application/json",
)
async def builder_api_json() -> str:
    api_data = {
        "name": "BogFolderBuilder",
        "summary": "High-level builder for Niagara .bog graphs with validation and layout.",
        "methods": [
            {"name": "start_sub_folder", "params": [{"name": "name", "type": "str"}]},
            {"name": "end_sub_folder", "params": []},
            {
                "name": "add_component",
                "params": [
                    # ✅ use 'type' not 'comp_type'
                    {"name": "type", "type": "str"},
                    {"name": "name", "type": "str"},
                    {"name": "properties", "type": "dict|null"},
                    {"name": "actions", "type": "dict|null"},
                ],
            },
            {
                "name": "add_numeric_writable",
                "params": [
                    {"name": "name", "type": "str"},
                    {"name": "default_value", "type": "float|int|bool|null"},
                ],
            },
            {
                "name": "add_boolean_writable",
                "params": [
                    {"name": "name", "type": "str"},
                    {"name": "default_value", "type": "bool|null"},
                ],
            },
            # ✅ document link call shape so model doesn't guess
            {
                "name": "add_link",
                "params": [
                    {"name": "src", "type": "str"},
                    {"name": "src_slot", "type": "str"},
                    {"name": "tgt", "type": "str"},
                    {"name": "tgt_slot", "type": "str"},
                ],
            },
            {
                "name": "to_xml_string",
                "returns": "str",
                "desc": "Serializes the entire BOG structure to an XML string.",
            },
            {"name": "save", "desc": "DEPRECATED in MCP mode. Do not use."},
        ],
        # Optional: declare the execution contract explicitly
        "execution_contract": "Generated module must define build() -> str and return to_xml_string(). No file writes.",
    }
    return json.dumps(api_data, indent=2)


# ---- Export ASGI app for uvicorn ----
app = mcp.http_app()
