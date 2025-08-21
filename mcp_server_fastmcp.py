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

from fastmcp import FastMCP
from pydantic import BaseModel, Field

# Analyzer is optional; guard import
try:
    from bog_builder import Analyzer
except Exception:
    Analyzer = None  # type: ignore

BASE_DIR = Path(__file__).resolve().parent
EXAMPLES_DIR = BASE_DIR / "examples"
GENERATED_DIR = BASE_DIR / "generated"
GENERATED_DIR.mkdir(exist_ok=True)


# NEW: accept synthesized code from the agent, write it, execute it, and save outputs to output_dir
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
    description: Optional[str] = Field(description="Detailed explanation of what the example does.")
    inputs: List[ExampleParameter] = Field(description="A list of input parameters the example requires.")

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

# NEW: batch fetch multiple example sources (for the agent to study ≥5 at once)
@mcp.tool(
    name="get_example_sources",
    description="Return sources for multiple example scripts in one call."
)
async def get_example_sources(example_names: List[str]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for name in example_names:
        p = EXAMPLES_DIR / name
        if p.is_file():
            out.append({"name": name, "source": p.read_text(encoding="utf-8")})
    return out

@mcp.tool(
    name="analyze_station",
    description="Analyze a Niagara archive and optionally generate kitControl charts.",
)
async def analyze_station(req: AnalyzeRequest) -> Dict[str, Any]:
    if Analyzer is None:
        raise RuntimeError("Analyzer module is not available in this environment")
    file_path = Path(req.file_path)
    if not file_path.is_file():
        raise FileNotFoundError(f"File not found: {file_path}")
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

# Runs a curated example and saves output into output_dir
@mcp.tool(
    name="run_example",
    description="Execute an example script on the server and save its output (.bog, etc.) into output_dir."
)
async def run_example(example_name: str, output_dir: str) -> Dict[str, Any]:
    """
    Attempts to run examples/<example_name> in one of two ways:
    1) If the script defines a callable `build(output_dir: str)`, import and call it.
    2) Otherwise, execute it as a script in a subprocess, passing OUTPUT_DIR via environment.
    """
    example_path = EXAMPLES_DIR / example_name
    if not example_path.is_file():
        raise FileNotFoundError(f"Example not found: {example_name}")

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Try import-and-call first
    try:
        spec = importlib.util.spec_from_file_location("example_mod", str(example_path))
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            sys.modules["example_mod"] = mod
            spec.loader.exec_module(mod)
            build = getattr(mod, "build", None)
            if callable(build):
                result = build(str(out_dir))
                return {
                    "status": "ok",
                    "strategy": "inprocess_build",
                    "example": example_name,
                    "output_dir": str(out_dir),
                    "result": result,
                }
    except Exception:
        # fall back to subprocess
        pass

    env = os.environ.copy()
    env["OUTPUT_DIR"] = str(out_dir)
    cmd = [sys.executable, str(example_path)]
    try:
        proc = subprocess.run(cmd, env=env, capture_output=True, text=True, cwd=str(EXAMPLES_DIR))
        ok = (proc.returncode == 0)
        return {
            "status": "ok" if ok else "error",
            "strategy": "subprocess",
            "example": example_name,
            "output_dir": str(out_dir),
            "returncode": proc.returncode,
            "stdout": proc.stdout[-4000:],
            "stderr": proc.stderr[-4000:],
        }
    except Exception as e:
        return {
            "status": "error",
            "strategy": "subprocess",
            "example": example_name,
            "output_dir": str(out_dir),
            "error": str(e),
        }



@mcp.tool(
    name="run_generated_script",
    description="Write provided Python code to a file, execute it, and save outputs into output_dir."
)
async def run_generated_script(
    filename: str,
    source_code: str,
    output_dir: str,
    bog_filename: Optional[str] = None,  # <— NEW
) -> Dict[str, Any]:
    """
    Expects the generated script to define:
        def build(output_dir: str) -> str|None
    If found, call it directly. Otherwise, run as a subprocess with OUTPUT_DIR/BOG_NAME in env.
    Returns the saved .bog path if determinable.
    """
    if not SAFE_NAME_RE.match(filename) or not filename.endswith(".py"):
        raise ValueError("Invalid filename. Use something like 'central_plant_synth.py'")

    out_dir = Path(output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    # Write code to generated/
    dst = (GENERATED_DIR / filename).resolve()
    dst.write_text(source_code, encoding="utf-8")

    # Make project dirs importable (for BogFolderBuilder, etc.)
    for p in {str(BASE_DIR), str(GENERATED_DIR)}:
        if p not in sys.path:
            sys.path.insert(0, p)

    def resolve_saved(candidate: Optional[str]) -> tuple[Optional[str], bool, Optional[int]]:
        if candidate:
            cand = (out_dir / candidate).resolve()
            if cand.is_file():
                return str(cand), True, cand.stat().st_size
        # fallback: newest .bog
        bogs = sorted(out_dir.glob("*.bog"), key=lambda p: p.stat().st_mtime, reverse=True)
        if bogs:
            p = bogs[0]
            return str(p.resolve()), True, p.stat().st_size
        return None, False, None

    # Try import-and-call build()
    try:
        import importlib.util
        from uuid import uuid4
        from io import StringIO
        from contextlib import redirect_stdout, redirect_stderr

        spec = importlib.util.spec_from_file_location(f"generated_mod_{uuid4().hex}", str(dst))
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            sys.modules[mod.__name__] = mod

            # Provide naming hint to the script
            if bog_filename:
                os.environ["BOG_NAME"] = bog_filename

            buf_out, buf_err = StringIO(), StringIO()
            with redirect_stdout(buf_out), redirect_stderr(buf_err):
                spec.loader.exec_module(mod)
                build = getattr(mod, "build", None)
                res = None
                if callable(build):
                    res = build(str(out_dir))

            saved = str(res) if res is not None else None
            if not saved:
                saved, exists, size = resolve_saved(bog_filename)
            else:
                sp = Path(saved).resolve()
                exists = sp.is_file()
                size = sp.stat().st_size if exists else None

            return {
                "status": "ok" if (saved and exists) else "ok",
                "strategy": "inprocess_build",
                "filename": filename,
                "output_dir": str(out_dir),
                "result": saved,
                "exists": bool(exists),
                "size_bytes": size,
                "stdout": buf_out.getvalue()[-4000:],
                "stderr": buf_err.getvalue()[-4000:],
            }
    except Exception as e:
        # fall through to subprocess; include why import/invoke failed
        import_err = str(e)
    else:
        import_err = None

    # Subprocess fallback
    env = os.environ.copy()
    env["OUTPUT_DIR"] = str(out_dir)
    if bog_filename:
        env["BOG_NAME"] = bog_filename
    cmd = [sys.executable, str(dst)]
    try:
        proc = subprocess.run(
            cmd, env=env, capture_output=True, text=True,
            cwd=str(GENERATED_DIR), timeout=240
        )
        ok = (proc.returncode == 0)
        saved, exists, size = resolve_saved(bog_filename)

        return {
            "status": "ok" if ok else "error",
            "strategy": "subprocess",
            "filename": filename,
            "output_dir": str(out_dir),
            "returncode": proc.returncode,
            "stdout": proc.stdout[-4000:],
            "stderr": (proc.stderr or "")[-4000:]
                     + (("\n[import_error]\n" + import_err) if import_err else ""),
            "result": saved,
            "exists": bool(exists),
            "size_bytes": size,
        }
    except Exception as e:
        return {
            "status": "error",
            "strategy": "subprocess",
            "filename": filename,
            "output_dir": str(out_dir),
            "error": str(e),
            "stderr": (("[import_error]\n" + import_err) if import_err else None),
        }


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
        "ctor": {
            "signature": "BogFolderBuilder(folder_name: str, debug: bool = True)",
            "params": [
                {"name": "folder_name", "type": "str", "desc": "Top-level folder name in the .bog"},
                {"name": "debug", "type": "bool", "default": True, "desc": "Print layout/validation hints"},
            ],
        },
        "methods": [
            {"name": "start_sub_folder", "params": [{"name": "name", "type": "str"}]},
            {"name": "end_sub_folder", "params": []},
            {"name": "get_current_path_str", "returns": "str"},
            {"name": "add_component", "params": [
                {"name": "comp_type", "type": "str"},
                {"name": "name", "type": "str"},
                {"name": "properties", "type": "dict|null"},
                {"name": "actions", "type": "dict|null"},
            ]},
            {"name": "add_numeric_writable"},
            {"name": "add_boolean_writable"},
            {"name": "add_enum_writable"},
            {"name": "add_numeric_switch"},
            {"name": "add_numeric_select"},
            {"name": "add_multi_vibrator"},
            {"name": "add_counter"},
            {"name": "add_link"},
            {"name": "add_reduction_block"},
            {"name": "save"},
        ],
    }
    return json.dumps(api_data, indent=2)

# ---- Export ASGI app for uvicorn ----
app = mcp.http_app()
