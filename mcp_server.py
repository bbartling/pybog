

from __future__ import annotations

import ast
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from pydantic import BaseModel, Field

from bog_builder.analyzer import Analyzer



BASE_DIR = Path(__file__).resolve().parent
EXAMPLES_DIR = BASE_DIR / "examples"


app = FastAPI(
    title="Bog Builder MCP Server",
    description="Expose example scripts as callable endpoints. This is a demonstration of the Model Context Protocol.",
)



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



class AnalyzeRequest(BaseModel):
    """Schema for analysis requests."""

    file_path: str
    plots_dir: Optional[str] = None


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
            required=True,
        )
    ]

    return ExampleDetails(name=script_path.name, description=docstring, inputs=inputs)




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


@app.get("/examples/{example_name}/source")
async def get_example_source(example_name: str) -> dict:
    """
    Returns the raw Python source of a specific example so LLMs can ingest code via JSON.
    """
    example_path = EXAMPLES_DIR / example_name
    if not example_path.is_file():
        raise HTTPException(status_code=404, detail=f"Example not found: {example_name}")
    return {"name": example_name, "source": example_path.read_text(encoding="utf-8")}



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
    


@app.get("/builder-api.json")
async def builder_api_json():
    # Static summary tailored for agents; you can enrich from inspect() later.
    return JSONResponse({
        "name": "BogFolderBuilder",
        "summary": "High-level builder for Niagara .bog graphs with validation and layout.",
        "ctor": {
            "signature": "BogFolderBuilder(folder_name: str, debug: bool = True)",
            "params": [
                {"name": "folder_name", "type": "str", "desc": "Top-level folder name in the .bog"},
                {"name": "debug", "type": "bool", "default": True, "desc": "Print layout/validation hints"}
            ]
        },
        "methods": [
            {"name": "start_sub_folder", "params": [{"name": "name", "type": "str"}], "raises": ["ValueError"]},
            {"name": "end_sub_folder", "params": [], "raises": ["ValueError"]},
            {"name": "get_current_path_str", "returns": "str"},
            {"name": "add_component", "params": [
                {"name":"comp_type","type":"str"},
                {"name":"name","type":"str"},
                {"name":"properties","type":"dict|null"},
                {"name":"actions","type":"dict|null"}
            ], "raises": ["ValueError"]},
            {"name": "add_numeric_writable"},
            {"name": "add_boolean_writable"},
            {"name": "add_enum_writable"},
            {"name": "add_numeric_switch"},
            {"name": "add_numeric_select"},
            {"name": "add_multi_vibrator"},
            {"name": "add_counter"},
            {"name": "add_link", "params": [
                {"name":"source_comp_name","type":"str"},
                {"name":"source_slot","type":"str"},
                {"name":"target_comp_name","type":"str"},
                {"name":"target_slot","type":"str"},
                {"name":"link_type","type":"str","default":"b:Link"},
                {"name":"converter_type","type":"str|null"}
            ], "raises": ["ValueError"], "notes":"Auto adds conversion links for common type mismatches"},
            {"name": "add_reduction_block", "params": [
                {"name":"block_type","type":"str"},
                {"name":"final_output_name","type":"str"},
                {"name":"input_names","type":"List[str]"}
            ], "raises":["ValueError"]},
            {"name": "save", "params":[{"name":"file_path","type":"str"}], "raises":["ValueError","OSError"]}
        ]
    })
