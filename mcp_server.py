

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
    
