"""
generic_agent.py
------------------

This module defines a generic, interactive agent that can translate
high‑level natural language descriptions of HVAC control systems into
Niagara Baja Object Graphs (``.bog``).  It leverages Google’s Gemini
API to classify user requirements and extract any adjustable
parameters, then uses the local ``bog_builder`` library (and a
collection of example scripts) to construct the appropriate control
logic.

The agent supports a chat‑like workflow: when executed on the
command‑line it will prompt the user for a description of the desired
control sequence, call the Gemini model to interpret the request and
then build the corresponding ``.bog`` file.  If the description
matches a known system type (e.g. a central plant with boiler and
chiller, or any of the example scripts in ``pybog/pybog‑develop``)
the agent will invoke the relevant builder.  Otherwise it warns the
user that it cannot handle the request.

To use the agent you must supply a valid ``GOOGLE_API_KEY`` as an
environment variable.  For example:

    export GOOGLE_API_KEY='your_google_api_key_here'
    python generic_agent.py

At runtime the script will interactively ask for a description and
generate a ``.bog`` file in the ``output`` subfolder.  You can
override the destination via the ``--output`` flag.

This file does not depend on the MCP server used by the original
``agent.py``; instead it executes example scripts locally or calls
specialised builder functions.  It is meant as a foundation for
building more sophisticated conversational interfaces for HVAC control
design.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import google.generativeai as genai

# Third‑party builder imports
from bog_builder import BogFolderBuilder



###############################################################################
# Data structures
###############################################################################

@dataclass
class ToolInfo:
    """Metadata about a buildable example or system type.

    Attributes
    ----------
    name: str
        Identifier used by Gemini and by the agent when selecting a tool.
    description: str
        Human‑readable description used in the LLM prompt.  Should be
        concise but informative.
    handler: Any
        A callable or special token.  If ``handler`` is a callable,
        executing the tool means invoking this function.  If it is the
        string ``"script"`` the agent will attempt to load and execute
        a Python file matching ``name`` from the examples directory.
    """

    name: str
    description: str
    handler: Any


###############################################################################
# Configuration
###############################################################################

EXAMPLES_DIR = os.path.join(os.path.dirname(__file__), "pybog", "pybog-develop", "examples")
DEFAULT_OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")


###############################################################################
# Google API setup
###############################################################################

def init_gemini() -> Optional[genai.GenerativeModel]:
    """Configure and return the Gemini model if an API key is set.

    Returns
    -------
    genai.GenerativeModel | None
        A configured Gemini model or None if the API key is missing.
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("❌ GOOGLE_API_KEY environment variable not set. Unable to use Gemini.")
        return None
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.5-flash")
        return model
    except Exception as e:
        print(f"❌ Failed to configure Gemini: {e}")
        return None


###############################################################################
# Tool discovery and execution
###############################################################################

def discover_example_tools() -> List[ToolInfo]:
    """Inspect the examples directory and construct ToolInfo entries.

    Each Python file in the examples directory is treated as a potential
    tool.  A short description is extracted from the file's top‑level
    docstring or comment.  Tools defined here are executed by
    importing the module and calling its ``main()`` function with an
    ``--output_dir`` argument.

    Returns
    -------
    List[ToolInfo]
        A list of discovered example tools.
    """
    tools: List[ToolInfo] = []
    if not os.path.isdir(EXAMPLES_DIR):
        return tools
    for filename in os.listdir(EXAMPLES_DIR):
        if not filename.endswith(".py"):
            continue
        path = os.path.join(EXAMPLES_DIR, filename)
        desc = extract_file_description(path)
        tools.append(ToolInfo(name=filename, description=desc, handler="script"))
    return tools


def extract_file_description(path: str) -> str:
    """Extract a short description from the given Python file.

    It looks for a triple‑quoted string or a comment at the top of the
    file.  If no description can be found, it uses the filename.

    Parameters
    ----------
    path: str
        Absolute path to the Python file.

    Returns
    -------
    str
        A description string.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception:
        return os.path.basename(path)
    doc = ""
    # Check for triple quoted docstring
    in_doc = False
    for line in lines[:40]:
        stripped = line.strip()
        if stripped.startswith("\"\"\"") or stripped.startswith("'''"):
            if in_doc:
                break
            in_doc = True
            # remove starting quotes
            doc = stripped.strip("\"'")
            continue
        if in_doc:
            doc += " " + stripped.strip("\"'")
        if not in_doc and stripped.startswith("#"):
            # single line comment
            return stripped.lstrip("#").strip()
    return doc.strip() if doc else os.path.basename(path)


def assemble_tools() -> List[ToolInfo]:
    """Combine built‑in system types with discovered example scripts.

    Returns
    -------
    List[ToolInfo]
        Combined list of tools available to the agent.
    """
    tools: List[ToolInfo] = []
    # Add each example script
    tools.extend(discover_example_tools())
    return tools


def execute_tool(tool: ToolInfo, output_file: str) -> Optional[str]:
    """Execute the specified tool and write its output to ``output_file``.

    Parameters
    ----------
    tool: ToolInfo
        The tool definition returned by ``assemble_tools``.
    output_file: str
        Absolute path where the resulting ``.bog`` should be saved.

    Returns
    -------
    Optional[str]
        The absolute path to the generated file on success, or None on
        failure.
    """
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    try:
        if callable(tool.handler):
            # For callable handlers we need to instantiate a builder and call
            builder = BogFolderBuilder("HVACSystem", debug=False)
            # Attempt to inspect the function signature to see if it expects a builder
            # and setpoints.  We pass only the builder; higher‑level wrappers can
            # customise setpoints if desired.
            handler_func = tool.handler
            handler_func(builder)  # type: ignore[call-arg]
            builder.save(output_file)
            return os.path.abspath(output_file)
        elif tool.handler == "script":
            # Execute the script's main() function with output_dir
            script_path = os.path.join(EXAMPLES_DIR, tool.name)
            module_name = f"examples_{tool.name.replace('.', '_')}"
            spec = importlib.util.spec_from_file_location(module_name, script_path)
            if spec is None or spec.loader is None:
                print(f"❌ Could not load script {tool.name}")
                return None
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            # Determine output directory and run main
            out_dir = os.path.dirname(output_file)
            if hasattr(module, "main"):
                # Build args list to specify output directory.  Many example scripts
                # accept "--output_dir" to control where the .bog is saved.
                try:
                    module.main(["--output_dir", os.path.dirname(output_file)])  # type: ignore[arg-type]
                except TypeError:
                    # Some scripts may not accept arguments; call without args
                    module.main()  # type: ignore[arg-type]
                # Scripts typically write to the specified output directory using
                # their script name as the .bog filename.  Attempt to locate
                # that file and move it to ``output_file``.
                produced: Optional[str] = None
                base_name = os.path.splitext(tool.name)[0] + ".bog"
                # primary candidate
                candidate = os.path.join(os.path.dirname(output_file), base_name)
                if os.path.isfile(candidate):
                    produced = candidate
                else:
                    # fallback: search the entire specified directory
                    for root, _, files in os.walk(os.path.dirname(output_file)):
                        for f in files:
                            if f == base_name:
                                produced = os.path.join(root, f)
                                break
                        if produced:
                            break
                if produced:
                    # Replace or move produced file to desired name
                    if os.path.abspath(produced) != os.path.abspath(output_file):
                        os.replace(produced, output_file)
                    return os.path.abspath(output_file)
                else:
                    print(f"❌ Could not locate output from {tool.name}")
                    return None
            else:
                print(f"❌ Script {tool.name} does not define a main() function")
                return None
        else:
            print(f"❌ Unknown handler type for tool {tool.name}")
            return None
    except Exception as e:
        print(f"❌ Failed to execute tool {tool.name}: {e}")
        return None


###############################################################################
# LLM interaction
###############################################################################

def classify_description(
    model: genai.GenerativeModel, description: str, tools: List[ToolInfo]
) -> Tuple[Optional[str], Dict[str, Any]]:
    """Ask the Gemini model to classify the user's description.

    The prompt instructs the model to choose a ``system_type`` from the
    available tools and extract any relevant numeric parameters.  The
    output must be valid JSON with two top‑level keys: ``system_type``
    (string) and ``parameters`` (object).  The ``system_type`` should
    match exactly one of the names in ``tools``; if none fit it should
    be "unknown".

    Parameters
    ----------
    model: genai.GenerativeModel
        The configured Gemini model.
    description: str
        The user's free‑form description of the HVAC system.
    tools: List[ToolInfo]
        List of available system types/scripts to choose from.

    Returns
    -------
    Tuple[str|None, Dict[str, Any]]
        The selected system type and a dictionary of parameters.  If
        the model cannot produce a valid JSON or selects an unknown
        system, the first element is None.
    """
    tool_names = [t.name for t in tools]
    prompt = f"""
You are an HVAC controls design assistant.  Given a natural language
description of a desired control sequence, you must classify it into
one of the known system types and extract any adjustable numeric
setpoints.  The known system types are: {tool_names}.

For example, a "central_plant" system has a boiler and chiller with
heating and cooling start/stop setpoints and optionally a free
cooling range.  Other system types correspond to example scripts
located in the local repository and may not accept parameters.  If
the description does not match any known type, return "unknown".

Respond with a JSON object containing exactly two keys: "system_type"
(string) and "parameters" (object).  The value of "system_type"
must be one of the known system types or "unknown".  The "parameters"
object should include any numeric setpoints that appear in the
description.  Use snake_case keys like "heat_start", "heat_stop",
"cool_start", "cool_stop", "free_low", and "free_high" for a
central_plant.  If no parameters are found leave the object empty.

Description: "{description}"

Respond with JSON only.
"""
    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        # Replace single quotes with double to aid JSON parsing
        safe_text = text.replace("'", '"')
        data = json.loads(safe_text)
        system_type = data.get("system_type")
        params = data.get("parameters", {})
        if system_type not in tool_names and system_type != "unknown":
            return None, {}
        return system_type, params
    except Exception as e:
        print(f"❌ Gemini classification error: {e}")
        return None, {}


###############################################################################
# Main CLI
###############################################################################

def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Interactively build Niagara .bog files from natural language "
            "descriptions using Gemini for classification."
        )
    )
    parser.add_argument(
        "--output",
        default=None,
        help=(
            "Destination .bog file.  If omitted, the file will be placed "
            "in the 'output' subdirectory with a name derived from the system type."
        ),
    )
    args = parser.parse_args(argv)

    model = init_gemini()
    tools = assemble_tools()
    if not tools:
        print("❌ No tools discovered.  Ensure examples are available and the central plant builder is imported.")
        return
    if model is None:
        print("❌ Gemini model unavailable.  Unable to classify descriptions.")
        return

    # Prompt user for description
    print(
        "Please describe the HVAC control system you wish to build.\n" +
        "For example: 'Create a central plant with heating and cooling setpoints of 40°F/45°F and 75°F/70°F with a free cooling range between 50 and 60°F.'\n"
    )
    try:
        description = input("Description: ")
    except EOFError:
        print("No description provided.  Exiting.")
        return
    description = description.strip()
    if not description:
        print("No description provided.  Exiting.")
        return

    system_type, params = classify_description(model, description, tools)
    if not system_type or system_type == "unknown":
        print("⚠️  Unable to recognise the requested system.  Please try again with a clearer description.")
        return

    # Find the matching tool
    chosen_tool = next((t for t in tools if t.name == system_type), None)
    if chosen_tool is None:
        print(f"⚠️  System type '{system_type}' is not available.")
        return

    # Determine output file path
    if args.output:
        output_path = os.path.abspath(args.output)
    else:
        base_name = f"{system_type}.bog"
        output_path = os.path.join(DEFAULT_OUTPUT_DIR, base_name)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # For other scripts delegate to execute_tool
    result = execute_tool(chosen_tool, output_path)
    if result:
        print(f"✅ Generated .bog file at: {result}")
    else:
        print("❌ Failed to generate the .bog file.")


if __name__ == "__main__":
    main()