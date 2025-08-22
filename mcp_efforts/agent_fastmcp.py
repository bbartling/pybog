# agent_fastmcp.py (complete rewrite)

import asyncio
import json
import os
from typing import List, Dict, Any, Mapping
from collections import defaultdict
from pathlib import Path

from fastmcp import Client

# =========================
# Config
# =========================
MCP_SERVER_URL = "http://127.0.0.1:8000/mcp"
FIXED_OUTPUT_DIR = Path("./fixed_output")
REQUIRED_EXAMPLES = 10
MAX_EXAMPLES_FOR_SYNTH = 8
MAX_ATTEMPTS = 5
BOG_FILENAME = "synthesized_hvac.bog"

# =========================
# LLM (Gemini)
# =========================
gemini_model = None
try:
    import google.generativeai as genai
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    if not GOOGLE_API_KEY:
        print("❌ GOOGLE_API_KEY not set — this agent requires an LLM.")
        raise SystemExit(1)
    genai.configure(api_key=GOOGLE_API_KEY)
    gemini_model = genai.GenerativeModel("gemini-1.5-flash")
except Exception as e:
    print(f"❌ Gemini unavailable: {e} — this agent requires an LLM.")
    raise SystemExit(1)

# =========================
# Metrics
# =========================
MCP_CALLS = 0
LLM_CALLS = 0
MCP_TOOL_COUNTS = defaultdict(int)

async def call_tool_counted(client: Client, tool_name: str, args: dict, timeout: int = 40):
    global MCP_CALLS, MCP_TOOL_COUNTS
    MCP_CALLS += 1
    MCP_TOOL_COUNTS[tool_name] += 1
    return await asyncio.wait_for(client.call_tool(tool_name, args), timeout=timeout)


INSTRUCTIONS_PATH = "context/old/BACKUP_llm_bog_instructions.txt"


def _load_context_pack() -> str:
    try:
        with open(INSTRUCTIONS_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""

def build_system_prompt(last_error: str | None = None, api_info: dict | None = None) -> str:
    context_pack = _load_context_pack()  # 👈 pull in your updated file
    # ... then prepend it to your system message
    sysmsg = (
        context_pack + "\n\n" +  # 👈 add this line
        "You are a senior Niagara/BAS code generator. Generate a single, complete Python module.\n"
        # (rest of your system prompt)
    )
    # (rest unchanged)
    return sysmsg

# =========================
# Normalization helpers (Pydantic / RootModel safe)
# =========================
def _to_plain(obj):
    """Recursively convert Pydantic models / RootModels / dataclasses to plain Python."""
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, Mapping):
        return {k: _to_plain(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_to_plain(x) for x in obj]
    if hasattr(obj, "model_dump"):   # Pydantic v2 BaseModel
        return _to_plain(obj.model_dump())
    if hasattr(obj, "root"):         # RootModel-like
        try:
            return _to_plain(getattr(obj, "root"))
        except Exception:
            pass
    try:
        import dataclasses
        if dataclasses.is_dataclass(obj):
            return _to_plain(dataclasses.asdict(obj))
    except Exception:
        pass
    try:
        return _to_plain(vars(obj))
    except Exception:
        return obj

def _to_dict_list(items):
    """Ensure we always end up with list[dict]."""
    plain = _to_plain(items)
    if plain is None:
        return []
    if isinstance(plain, dict):
        return [plain]
    if isinstance(plain, list):
        out = []
        for x in plain:
            x = _to_plain(x)
            if isinstance(x, dict):
                out.append(x)
            else:
                out.append({"value": x})
        return out
    return [{"value": plain}]

# =========================
# API inference & prompting
# =========================
def _api_from_examples(example_sources: list[dict]) -> dict:
    """
    Infer allowed methods and constructor usage from the example source bundle.
    """
    import re
    srcs = []
    for it in _to_dict_list(example_sources):
        s = (it.get("source") or it.get("code") or it.get("content") or "")
        if s:
            srcs.append(s)
    joined = "\n".join(srcs)

    # Methods like builder.add_numeric_writable(...), builder.start_sub_folder(...), etc.
    meths = sorted(set(re.findall(r'\bbuilder\.([A-Za-z_][A-Za-z0-9_]*)\s*\(', joined)))
    # Constructor usage: BogFolderBuilder("Name"...) patterns
    ctor_requires_folder = bool(re.search(r'BogFolderBuilder\s*\(\s*["\']', joined))
    return {"methods": meths, "ctor_requires_folder_name": ctor_requires_folder}

def _retry_hint(last_error: str) -> str:
    e = (last_error or "").lower()
    if "missing 1 required positional argument: 'folder_name'" in e:
        return "Use BogFolderBuilder(folder_name='SomeName'). 'folder_name' is required."
    if "object has no attribute 'add_device'" in e:
        return "Do not call 'add_device'. Use 'add_component' or typed helpers like 'add_numeric_writable'."
    if "no attribute 'add_link'" in e or "add_link(" in e and "not found" in e:
        return "Check method name and signature; use builder.add_link(source_name, 'out', target_name, 'in', link_type='baja:Slot')."
    return ""

def build_system_prompt(last_error: str | None = None, api_info: dict | None = None) -> str:
    context_pack = _load_context_pack()  # 👈 pull in your updated file
    # ... then prepend it to your system message
    sysmsg = (
        context_pack + "\n\n" +  # 👈 add this line
        "You are a senior Niagara/BAS code generator. Generate a single, complete Python module.\n"
    )

    api_part = ""
    if api_info:
        methods = ", ".join(api_info.get("methods", [])) or "(no methods inferred)"
        ctor_note = "REQUIRED" if api_info.get("ctor_requires_folder_name") else "UNKNOWN"
        api_part = (
            "\n\nKNOWN API INFERRED FROM EXAMPLES\n"
            f"- BogFolderBuilder(folder_name: str) is {ctor_note}.\n"
            f"- Allowed/seen methods: {methods}\n"
            "- If a method you want is not listed, use `add_component(...)` or a seen helper instead.\n"
        )

    sysmsg = (
        "You are a senior Niagara/BAS code generator. Generate a single, complete Python module.\n"
        "Strict rules:\n"
        f"{api_part}\n"
        "Output ONLY raw Python code. No prose or markdown fences."
        "Define exactly one function: `build() -> str` EXACTLY like example py files provided."
        "The function must not take any arguments."
        """    # -------- Save .bog --------
        os.makedirs(args.output_dir, exist_ok=True)
        out_path = os.path.join(args.output_dir, f"{script_filename}.bog")
        builder.save(out_path)
        print(f"Created Niagara .bog at: {out_path}")
        """

    )
    if last_error:
        sysmsg += (
            "\n\nCRITICAL: The previous attempt failed at runtime on the server. "
            "You MUST correct your code to resolve this.\n"
            f"ERROR DETAILS:\n---\n{last_error}\n---\n"
        )
        hint = _retry_hint(last_error)
        if hint:
            sysmsg += f"\nSPECIFIC FIX HINT: {hint}"
    return sysmsg

# =========================
# LLM flows
# =========================
def llm_choose_examples(examples: List[Dict[str, Any]], user_goal: str) -> List[str]:
    global LLM_CALLS
    LLM_CALLS += 1

    examples = _to_dict_list(examples)
    slim = []
    for e in examples:
        name = (e.get("name") or e.get("filename") or e.get("id") or "").strip()
        desc = (e.get("description") or e.get("desc") or "").strip()
        if name:
            slim.append({"name": name, "desc": desc})

    prompt = f"""
You are a BAS/Niagara controls expert.

TASK: From the list below, choose AT LEAST {REQUIRED_EXAMPLES} examples most relevant
to the user's goal. Return ONLY a JSON array of names, min {REQUIRED_EXAMPLES}, max {MAX_EXAMPLES_FOR_SYNTH}.

USER GOAL:
{user_goal}

EXAMPLES (name + short description):
{json.dumps(slim, indent=2)}
"""
    resp = gemini_model.generate_content(prompt)
    text = (resp.text or "").strip().replace("```json", "").replace("```", "").strip()
    chosen = json.loads(text)
    names = {e.get("name") for e in examples}
    chosen = [n for n in chosen if n in names]
    if len(chosen) < REQUIRED_EXAMPLES:
        raise RuntimeError(f"LLM selected insufficient examples: {len(chosen)}")
    return chosen[:MAX_EXAMPLES_FOR_SYNTH]

def llm_synthesize_script(
    example_sources: List[Dict[str, Any]],
    user_goal: str,
    last_error: str | None,
    api_info: dict | None = None
) -> str:
    global LLM_CALLS
    LLM_CALLS += 1

    srcs = _to_dict_list(example_sources)

    # Build a readable “code bundle” for the LLM
    bundle_lines = []
    for item in srcs:
        name = (item.get("name") or item.get("filename") or "example.py").strip()
        source = (item.get("source") or item.get("code") or item.get("content") or "").rstrip()
        if source:
            bundle_lines.append(f"# ========== {name} ==========\n{source}\n")
    bundle = "\n".join(bundle_lines)

    system_prompt = build_system_prompt(last_error=last_error, api_info=api_info)
    user_prompt = f"""
USER GOAL:
{user_goal}

FOLLOW EXAMPLES EXACTLY. Copy method names and call shapes you see.
If a method is not listed in the inferred API, use `add_component(...)` or a seen helper.

VETTED EXAMPLES (study these; synthesize new code, DO NOT paste verbatim):
{bundle}
"""
    resp = gemini_model.generate_content([system_prompt, user_prompt])
    code = (resp.text or "").strip().replace("```python","").replace("```","").strip()
    if "def build()" not in code:
        raise RuntimeError("LLM did not produce a `build()` function.")
    # Guard against known bad invents
    DISALLOWED = {"add_device", "create_device", "wire(", "connect_device"}
    if any(x in code for x in DISALLOWED):
        raise RuntimeError("Generated code used a disallowed/unknown method; must follow examples exactly.")
    return code

# =========================
# Example expansion policy
# =========================
def expand_chosen_examples(all_examples: list[dict], chosen: list[str]) -> list[str]:
    """
    If we fail, add more examples that look structurally useful.
    Heuristics: prefer names with 'reset', 'schedule', 'switch', 'select', 'bool', 'hot_water'.
    """
    have = set(chosen)
    names = [e.get("name") for e in _to_dict_list(all_examples)]
    priority_terms = ["reset", "schedule", "switch", "select", "bool", "hot_water"]
    extra = []
    for term in priority_terms:
        for n in names:
            if n and n not in have and term in n.lower():
                extra.append(n)
    extra = extra[: max(0, MAX_EXAMPLES_FOR_SYNTH - len(chosen))]
    return chosen + extra

# =========================
# MCP wrappers
# =========================
async def mcp_list_examples(client: Client) -> List[Dict[str, Any]]:
    res = await call_tool_counted(client, "list_examples", {}, timeout=20)
    return _to_dict_list(res.data)

async def mcp_get_sources(client: Client, names: List[str]) -> List[Dict[str, Any]]:
    names = names or []
    res = await call_tool_counted(
        client, "get_example_sources", {"example_names": names}, timeout=40
    )
    return _to_dict_list(res.data)

async def mcp_run_generated(client: Client, code: str) -> Dict[str, Any]:
    res = await call_tool_counted(
        client,
        "run_generated_script",
        {"filename": "agent_synth.py", "source_code": code},
        timeout=240
    )
    return res.data or {}

# =========================
# Main Retry Loop
# =========================
async def try_build_loop(client: Client, user_goal: str, examples: List[Dict[str,Any]]):
    """
    1. Pick examples and fetch sources
    2. Synthesize Python code via LLM (strict example-following)
    3. Send code to MCP server for execution
    4. On failure, expand examples and retry with error feedback
    5. On success, save BOG XML locally
    """
    # Initial selection
    chosen_names = llm_choose_examples(examples, user_goal)
    sources = await mcp_get_sources(client, chosen_names)

    last_error = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        print(f"\n🔁 Attempt {attempt}/{MAX_ATTEMPTS}: Synthesizing Python script...")

        api_info = _api_from_examples(sources)

        try:
            # ✅ Correct arg order: examples first, then goal
            code = llm_synthesize_script(sources, user_goal, last_error=last_error, api_info=api_info)
            print(f"🐍 Synthesized code (length: {len(code)} chars). Sending to MCP for execution...")
        except Exception as e:
            print(f"❌ Failed to synthesize code: {e}")
            last_error = f"Code synthesis failed: {e}"
            # Expand examples for next round
            chosen_names = expand_chosen_examples(examples, chosen_names)
            sources = await mcp_get_sources(client, chosen_names)
            continue

        # Execute the code on the server
        response = await mcp_run_generated(client, code)
        print("💻 MCP Server Response:")
        print(json.dumps(response, indent=2))

        status = (response.get("status") or "").lower()

        if status == "ok":
            bog_data = response.get("bog_data")
            if not bog_data:
                print("❌ Build succeeded but server returned no BOG data.")
                last_error = "Server execution was successful, but the `bog_data` field was empty."
                # Try expanding examples and retrying
                chosen_names = expand_chosen_examples(examples, chosen_names)
                sources = await mcp_get_sources(client, chosen_names)
                continue

            # Save client-side
            try:
                FIXED_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
                output_path = FIXED_OUTPUT_DIR / BOG_FILENAME
                output_path.write_text(bog_data, encoding="utf-8")
                print(f"✅ Build Succeeded! Saved {len(bog_data)} bytes to: {output_path.resolve()}")
                return {"ok": True, "path": str(output_path.resolve())}
            except Exception as e:
                print(f"❌ CRITICAL: Failed to save BOG data locally: {e}")
                return {"ok": False, "error": f"Failed to save file: {e}"}

        else:
            # Execution failed, prep error + expand examples, then retry
            error_msg = response.get("error", "Unknown error.")
            stderr = response.get("stderr", "")
            last_error = f"Error: {error_msg}\nStderr:\n{stderr}".strip()
            print(f"❗️ Attempt {attempt} failed. Retrying with error feedback...")

            chosen_names = expand_chosen_examples(examples, chosen_names)
            sources = await mcp_get_sources(client, chosen_names)

    print("❌ All attempts failed.")
    return {"ok": False, "error": last_error}

# =========================
# Orchestrator
# =========================
async def main():
    user_goal = (
        "Create a hot water reset schedule. It should take Outdoor Air Temperature (OAT) as an input "
        "and reset the Hot Water Supply Temperature Setpoint. When OAT is at 0, the setpoint should be 160. "
        "When OAT is at 50, the setpoint should be 110."
    )

    async with Client(MCP_SERVER_URL) as client:
        tools = [t.model_dump() for t in await asyncio.wait_for(client.list_tools(), timeout=10)]
        print("🤖 MCP Tools discovered:", [t.get("name") for t in tools])

        examples = await mcp_list_examples(client)
        print(f"📚 Found {len(examples)} examples on the server.")
        if not examples:
            print("❌ No examples on server to learn from. Aborting.")
            return

        # Kick off the build loop (this function now handles choosing & expanding examples)
        final_outcome = await try_build_loop(client, user_goal, examples)

        if not final_outcome["ok"]:
            print("\n---")
            print("❌ Final attempt failed. Last known error:")
            print(final_outcome.get("error"))
            print("---")

        # Metrics
        print("\n—— Stats ——")
        print("LLM calls:", LLM_CALLS)
        print("MCP calls:", MCP_CALLS)
        print("MCP tools:", dict(MCP_TOOL_COUNTS))

if __name__ == "__main__":
    asyncio.run(main())
