# agent_fastmcp.py
import asyncio
import json
import os
from typing import List, Dict, Any
from collections import defaultdict

from fastmcp import Client

# =========================
# Config
# =========================
MCP_SERVER_URL  = "http://127.0.0.1:8000/mcp"   # no trailing slash to avoid 307s
OUTPUT_DIR      = "/mnt/c/Users/ben/Niagara4.11/JENEsys"
REQUIRED_EXAMPLES = 5
MAX_EXAMPLES_FOR_SYNTH = 8
MAX_ATTEMPTS = 3
BOG_FILENAME = "synthesized_hvac.bog"           # guaranteed output name

# =========================
# LLM (Gemini) – REQUIRED
# =========================
gemini_model = None
try:
    import google.generativeai as genai
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    if not GOOGLE_API_KEY:
        print("❌ GOOGLE_API_KEY not set — this agent requires an LLM.")
        raise SystemExit(1)
    genai.configure(api_key=GOOGLE_API_KEY)
    gemini_model = genai.GenerativeModel("gemini-2.5-flash")
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

# =========================
# Utilities
# =========================
def _to_plain_dict(obj):
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "model_dump"):
        try:
            return obj.model_dump()
        except Exception:
            pass
    d = {}
    for key in ("name", "source", "description"):
        if hasattr(obj, key):
            d[key] = getattr(obj, key)
    if not d and hasattr(obj, "__dict__"):
        try:
            return dict(obj.__dict__)
        except Exception:
            pass
    return d

# =========================
# LLM helpers
# =========================
def build_system_prompt(last_error: str | None = None) -> str:
    constraints = [
        "Define exactly: build(output_dir: str) -> str | None",
        "Import and use BogFolderBuilder (assume it is installed on the server).",
        "Only use method signatures that exist; do NOT invent keyword args.",
        "Do NOT use an 'internal' kwarg anywhere.",
        "If env var BOG_NAME is set, save to Path(output_dir)/BOG_NAME; else use a safe default ending with .bog.",
        "Return the saved path as a string.",
    ]
    sysmsg = (
        "You are a senior Niagara/BAS code generator. Write ONE Python module that:\n"
        f"- {'; '.join(constraints)}\n"
        "Output ONLY Python code (no prose, no fences)."
    )
    if last_error:
        sysmsg += (
            "\n\nIMPORTANT: The previous attempt failed with this runtime error:\n"
            f"{last_error}\n"
            "Fix your code so this error cannot happen again."
        )
    return sysmsg

def llm_choose_examples(examples: List[Dict[str, Any]], user_goal: str) -> List[str]:
    """Ask the LLM to select >= REQUIRED_EXAMPLES example names."""
    global LLM_CALLS
    LLM_CALLS += 1

    slim = [{"name": e.get("name"), "desc": (e.get("description") or "")} for e in examples]
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

def llm_synthesize_script(user_goal: str, sources: List[Dict[str, Any]], last_error: str | None = None) -> str:
    """Produce a module that defines build(output_dir: str) and returns the saved .bog path."""
    global LLM_CALLS
    LLM_CALLS += 1

    sources = [_to_plain_dict(x) for x in sources]
    bundles = [{"name": x.get("name",""), "snippet": (x.get("source") or "")[:1800]} for x in sources]

    system = build_system_prompt(last_error=last_error)
    user = f"""
USER GOAL:
{user_goal}

VETTED EXAMPLES (study style and naming; synthesize new code — don't copy verbatim):
{json.dumps(bundles, indent=2)}
"""
    resp = gemini_model.generate_content([system, user])
    code = (resp.text or "").strip().replace("```python","").replace("```","").strip()
    if "def build(" not in code:
        raise RuntimeError("LLM did not produce a build(output_dir: str) function.")
    return code

# =========================
# MCP wrappers
# =========================
async def mcp_list_examples(client: Client) -> List[Dict[str, Any]]:
    res = await call_tool_counted(client, "list_examples", {}, timeout=20)
    return [_to_plain_dict(x) for x in (res.data or [])]

async def mcp_get_sources(client: Client, names: List[str]) -> List[Dict[str, Any]]:
    """Fetch example sources as JSON (batch first, then per-file fallback)."""
    names = names[:REQUIRED_EXAMPLES]
    # Batch first
    try:
        res = await call_tool_counted(client, "get_example_sources", {"example_names": names}, timeout=40)
        data = [_to_plain_dict(x) for x in (res.data or [])]
        out = [{"name": x.get("name",""), "source": x.get("source","")} for x in data
               if isinstance(x.get("name",""), str) and isinstance(x.get("source",""), str) and x.get("source","").strip()]
        if len(out) >= REQUIRED_EXAMPLES:
            return out
    except Exception as e:
        print(f"⚠️  get_example_sources failed: {repr(e)} — falling back to per-file.")

    # Per-file fallback
    outs: List[Dict[str, Any]] = []
    for n in names:
        try:
            r = await call_tool_counted(client, "get_example_source", {"example_name": n}, timeout=20)
            blob = _to_plain_dict(r.data or {})
            nm, src = blob.get("name") or n, blob.get("source") or ""
            if isinstance(src, str) and src.strip():
                outs.append({"name": nm, "source": src})
        except Exception as e:
            print(f"⚠️  get_example_source({n}) failed: {repr(e)}")
    return outs

async def mcp_run_generated(client: Client, filename: str, code: str, output_dir: str, bog_filename: str) -> Dict[str, Any]:
    res = await call_tool_counted(
        client,
        "run_generated_script",
        {
            "filename": filename,
            "source_code": code,
            "output_dir": output_dir,
            "bog_filename": bog_filename,  # requires server tool to accept this optional arg
        },
        timeout=240
    )
    return _to_plain_dict(res.data or {})

# =========================
# Retry loop: synthesize → run → feed errors → retry
# =========================
async def try_build_loop(client: Client, user_goal: str, sources: List[Dict[str,Any]], output_dir: str):
    last_error = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        print(f"\n🔁 Attempt {attempt}/{MAX_ATTEMPTS}: synthesizing…")
        code = llm_synthesize_script(user_goal, sources, last_error=last_error)
        print("🧪 synthesized code length:", len(code))

        res = await mcp_run_generated(client, "synth_module.py", code, output_dir, BOG_FILENAME)
        print(json.dumps(res, indent=2))

        status = (res.get("status") or "").lower()
        result_path = res.get("result")
        exists = res.get("exists")
        stderr = res.get("stderr")
        err_field = res.get("error")

        if status == "ok" and (result_path or exists):
            return {"ok": True, "result": res}

        last_error = (err_field or "") + ("\n" + stderr if stderr else "")
        last_error = last_error.strip() or "Unknown runtime error."

    return {"ok": False, "result": res}

# =========================
# Orchestrator
# =========================
async def main():
    # Plug your chat text here (the LLM decides what HVAC system to build)
    user_goal = "Generate an HVAC control .bog for the system implied by my chat; synthesize from vetted examples."

    async with Client(MCP_SERVER_URL) as client:
        tools = [t.model_dump() for t in await asyncio.wait_for(client.list_tools(), timeout=10)]
        print("🤖 tools discovered:", [t.get("name") for t in tools])

        examples = await mcp_list_examples(client)
        print("📚 examples available:", len(examples))
        if not examples:
            print("❌ No examples on server.")
            return

        chosen = llm_choose_examples(examples, user_goal)
        chosen = chosen[:REQUIRED_EXAMPLES]
        print("✅ chosen examples:", chosen)

        srcs = await mcp_get_sources(client, chosen)
        print("📦 sources fetched:", len(srcs))
        if len(srcs) < REQUIRED_EXAMPLES:
            print("❌ Not enough sources fetched for synthesis.")
            return

        outcome = await try_build_loop(client, user_goal, srcs, OUTPUT_DIR)
        if outcome["ok"]:
            res = outcome["result"]
            path = res.get("result")
            size = res.get("size_bytes")
            print(f"✅ Build succeeded. Saved: {path or '(path not returned)'}"
                  f"{' ('+str(size)+' bytes)' if size else ''}")
        else:
            print("❌ Final attempt failed.")

        # Metrics
        print("\n—— Stats ——")
        print("LLM calls:", LLM_CALLS)
        print("MCP calls:", MCP_CALLS)
        print("MCP tools:", dict(MCP_TOOL_COUNTS))

if __name__ == "__main__":
    asyncio.run(main())
