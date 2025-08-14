import os
import time
import textwrap
from pathlib import Path
from typing import List
import re

from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage
from azure.core.credentials import AzureKeyCredential

from pathlib import Path


# ----------------- CONFIG -----------------
ENDPOINT = "https://models.github.ai/inference"
MODEL = "xai/grok-3-mini"

GITHUB_TOKEN_ENV = "GITHUB_TOKEN"
CONTEXT_PATH = r"C:\Users\ben\Documents\llm-bog-gen\context_engineering\llm_bog_instructions_token_optimized.txt"

MODE = "bog"  # "bog" or "code"
# OUT_DIR = os.getcwd()
OUT_DIR = r"C:\Users\ben\OneDrive\Desktop\testing\examples\ai_generated_files"
Path(OUT_DIR).mkdir(parents=True, exist_ok=True)


# Token budgeting (approx: 1 token ~ 4 chars)
MAX_REQUEST_TOKENS = 8000
RESERVE_FOR_RESPONSE = 1500           # budget for model output
TARGET_PROMPT_TOKENS = MAX_REQUEST_TOKENS - RESERVE_FOR_RESPONSE
TOK_PER_CHAR = 1/4                    # heuristic
TARGET_PROMPT_CHARS = int(TARGET_PROMPT_TOKENS / TOK_PER_CHAR)

# ----------------- TASKS ------------------
THERMOSTAT_TASK = """
You are generating a Niagara 4 .bog builder script using the provided context.
Return ONLY a single Python file in [PYTHON]...[/PYTHON] tags (tests optional).
Requirements:
- Script must follow the builder API and folder/layout rules from the context.
- Name top-level folder "Thermostat_Demo".
- Create numeric/boolean writables for: SpaceTemp, HeatSP, CoolSP, Hysteresis, Mode (0=Off,1=Heat,2=Cool), FanAuto (bool), Output_HeatCmd, Output_CoolCmd, Output_FanCmd.
- Logic:
  - If Mode==1 (Heat) and SpaceTemp < HeatSP - Hysteresis => HeatCmd True.
  - If Mode==2 (Cool) and SpaceTemp > CoolSP + Hysteresis => CoolCmd True.
  - FanCmd True when HeatCmd or CoolCmd is True; if FanAuto==False, force FanCmd True.
- Put boolean/compare/math blocks in a subfolder "Logic".
- Respect Niagara naming (no names starting with a number) and ms strings for timer/delay if used.
- Accept -o output directory arg; save .bog with a hardcoded filename "thermostat_demo.bog".
- Add the sys.path append snippet like other examples from the context.
Return only the Python file in [PYTHON]...[/PYTHON] tags.
"""

PLAIN_CODE_TASK = """
Return [PYTHON] and [TESTS] blocks. Write a Python script that:
- Creates a list of N random numbers (N=50), sorts ascending with an in-place algorithm (e.g., insertion sort), prints first/last.
- Include unit tests that validate ascending order and length.
"""

TASK = THERMOSTAT_TASK if MODE == "bog" else PLAIN_CODE_TASK

# --------------- HELPERS ------------------
MODAL_RE = re.compile(r"\b(MUST|SHOULD|NEVER|ALWAYS|REQUIRED|PROHIBITED|MUST NOT|SHALL|SHALL NOT)\b", re.I)
KEYWORDS = [
    "Niagara", "kitControl", "bog", "WsAnnotation", "builder", "add_component", "add_link",
    "slot", "handle", "folder", "subfolder", "layout", "wsAnnotation", "Tridium",
    "Program Object", "NumericWritable", "BooleanWritable", "GreaterThan", "Switch",
    "compare", "math", "timer", "delay", "ms", "kitControl:", "b:WsAnnotation",
    "link", "target", "source", "inA", "inB", "out", "coords",
    "naming rules", "naming conventions", "precision", "defaultValue", "properties",
    "hysteresis", "Mode", "HeatSP", "CoolSP", "Fan", "Output_", "Logic"
]

def keep_line(s: str) -> bool:
    st = s.strip()
    if not st:
        return True
    if MODAL_RE.search(st):
        return True
    if any(k in st for k in KEYWORDS):
        return True
    if st.lstrip().startswith(("#","-","*")) and len(st) < 200:
        return True
    if re.search(r"\b(use|avoid|prefer|ensure|exact|format|tagged|naming)\b", st, re.I) and len(st) < 200:
        return True
    if len(st) > 280:
        return False
    if 40 <= len(st) <= 200 and st.endswith((".", ":", ";")):
        return True
    return False

def compress_context(raw: str, target_chars: int) -> str:
    lines = raw.splitlines()
    kept = [ln for ln in lines if keep_line(ln)]
    # de-dup preserve order
    seen = set(); dedup = []
    for ln in kept:
        key = ln.strip()
        if key not in seen:
            dedup.append(ln.rstrip())
            seen.add(key)
    # collapse blank runs
    collapsed = []
    blank = 0
    for ln in dedup:
        if ln.strip() == "":
            blank += 1
            if blank <= 1:
                collapsed.append("")
        else:
            blank = 0
            collapsed.append(ln)
    txt = ("\n".join(collapsed)).strip() + "\n"

    # If still too big, hard trim from the tail (keep “rulesy” head)
    if len(txt) > target_chars:
        txt = txt[:target_chars]
        # try not to cut mid-line
        last_nl = txt.rfind("\n")
        if last_nl > 0:
            txt = txt[:last_nl] + "\n"
    return txt

def approx_tokens_from_chars(n_chars: int) -> int:
    return int(n_chars * TOK_PER_CHAR)

def extract_between(text: str, tag: str) -> str:
    start, end = f"[{tag}]", f"[/{tag}]"
    i, j = text.find(start), text.find(end)
    if i == -1 or j == -1 or j <= i:
        return ""
    return text[i + len(start):j].strip()

def extract_code_fallback(text: str) -> str:
    m = re.search(r"```python\s+(.*?)```", text, re.S | re.I)
    if m:
        return m.group(1).strip()
    m = re.search(r"```\s+(.*?)```", text, re.S)
    if m:
        return m.group(1).strip()
    return ""

def chunk_text(s: str, max_len: int = 6000) -> List[str]:
    return [s[i:i+max_len] for i in range(0, len(s), max_len)]

def build_messages(context_text: str, task: str):
    msgs = []
    msgs.append(SystemMessage(content="You are a careful code generator. Follow the context exactly and obey output tags."))
    msgs.append(UserMessage(content="### OUTPUT SPEC\nReturn only:\n[PYTHON]\n# code here\n[/PYTHON]\n(Optional)\n[TESTS]\n# tests here\n[/TESTS]\nDO NOT include any other prose outside these tags."))

    # compress + enforce budget
    compressed = compress_context(context_text, TARGET_PROMPT_CHARS // 2)  # use ~half budget for context
    # put compressed context into 1–2 chunks
    chunks = chunk_text(compressed, max_len=6000)
    for idx, ch in enumerate(chunks, start=1):
        msgs.append(UserMessage(content=f"[CONTEXT CHUNK {idx}]\n{ch}"))

    # keep task small
    msgs.append(UserMessage(content=f"### TASK\n{task.strip()}"))
    # Print budgeting info
    total_chars = sum(len(m.content) for m in msgs)
    print(f"[Budget] prompt chars ~{total_chars} (~{approx_tokens_from_chars(total_chars)} tokens)")
    return msgs

# --------------- MAIN ---------------------
def main():
    token = os.environ.get(GITHUB_TOKEN_ENV)
    if not token:
        raise RuntimeError(f"Missing environment variable {GITHUB_TOKEN_ENV}")

    t0 = time.time()
    context_text = Path(CONTEXT_PATH).read_text(encoding="utf-8")
    messages = build_messages(context_text, THERMOSTAT_TASK if MODE == "bog" else PLAIN_CODE_TASK)

    client = ChatCompletionsClient(endpoint=ENDPOINT, credential=AzureKeyCredential(token))

    print(">>> Streaming from model...\n")
    response = client.complete(
        stream=True,
        messages=messages,
        model=MODEL,
        model_extras={'stream_options': {'include_usage': True}},
    )

    full_text = []
    usage = {}
    for update in response:
        if update.choices and update.choices[0].delta:
            delta = update.choices[0].delta.content or ""
            full_text.append(delta)
            print(delta, end="")
        if update.usage:
            usage = update.usage

    print("\n\n>>> Done.\n")
    raw = "".join(full_text)

    py_code = extract_between(raw, "PYTHON")
    if not py_code:
        py_code = extract_code_fallback(raw)
    tests = extract_between(raw, "TESTS")

    if not py_code:
        print("[DEBUG] No [PYTHON] block or code fences found. First 600 chars:\n", raw[:600])
        raise RuntimeError("No [PYTHON] block found in the model output.")

    Path(OUT_DIR).mkdir(parents=True, exist_ok=True)

    if MODE == "bog":
        out_py = Path(OUT_DIR) / "thermostat_demo_builder.py"
        out_py.write_text(py_code, encoding="utf-8")
        print(f"Saved builder script to: {out_py}")
        # Optional: run it to produce the .bog
        # import subprocess; subprocess.run(["python", str(out_py), "-o", OUT_DIR], check=True)
    else:
        full_code = textwrap.dedent(f"""
        {py_code}

        {tests if tests else ""}
        print("All tests passed!" if '{tests}'.strip() else "No tests block provided.")
        """)
        print("\n=== Running Generated Code ===")
        exec_globals = {}
        exec(full_code, exec_globals, exec_globals)

    if usage:
        print("\n--- Usage (as reported by API) ---")
        for k, v in usage.items():
            print(f"{k} = {v}")

    minutes = (time.time() - t0) / 60
    print(f"\nTotal script runtime: {minutes:.2f} minutes")

if __name__ == "__main__":
    main()
