from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import textwrap
import time
from pathlib import Path
from typing import List, Tuple, Optional

import google.generativeai as genai


# TODO test one:
# I need a central plant dual pump lead and lag staging logic where a bool point 
# can represent true or false and a loss of pump status if command is true with automatically 
# switch to lag pump if lead dies. Do a pump 1 and 2 where can switch between 
# lead or lag based on the bool point.

# TODO test two:
# Description: i need a bog file to make an AHU VAV leaving air temperature and 
# pressure operate setpoint control. Pressure variable fan would maintain an 
# inch WC and temperature control would be 55F constant setpoint.

# ========= Config =========
EXAMPLES_DIR = Path(os.getcwd()) / "examples"
DEFAULT_OUTPUT_DIR = Path(r"/mnt/c/Users/ben/Niagara4.11/JENEsys")
CONTEXT_DIR = Path(os.getcwd()) / "context"

MODEL_NAME = "gemini-2.5-flash"
MAX_ITERS_DEFAULT = 4

# nice to see metrics print at end
LLM_CALLS = 0
LLM_INPUT_TOKENS = 0
LLM_OUTPUT_TOKENS = 0


def init_gemini() -> Optional[genai.GenerativeModel]:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("❌ GOOGLE_API_KEY environment variable not set.")
        return None
    try:
        genai.configure(api_key=api_key)
        return genai.GenerativeModel(MODEL_NAME)
    except Exception as e:
        print(f"❌ Failed to configure Gemini: {e}")
        return None


# ========= Example harvesting =========

def _safe_read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""

def gather_examples() -> str:
    """
    Return all context text for the LLM.
    Prefer llms-full.txt if available, else concatenate all .txt files.
    No length clipping.
    """
    if not CONTEXT_DIR.is_dir():
        return ""

    full_path = CONTEXT_DIR / "llms-full.txt"
    if full_path.exists():
        return _safe_read(full_path)

    txt_files = sorted(CONTEXT_DIR.glob("*.txt"))
    chunks = []
    for p in txt_files:
        text = _safe_read(p)
        if text:
            chunks.append(f"\n=== FILE: {p.name} ===\n{text}\n=== CODE END ===\n")
    return "".join(chunks)


# ========= LLM prompts & helpers =========

def _extract_python_code(text: str) -> str:
    """
    Extract python code from LLM text. Accepts fenced blocks or raw.
    """
    if not text:
        return ""
    t = text.strip()
    # strip common fences
    fence = re.search(r"```(?:python)?\s*(.*?)```", t, flags=re.S)
    if fence:
        return fence.group(1).strip()
    return t

def _record_and_print_usage(resp, label: str) -> None:
    """Accumulate and print token usage for a single LLM call."""
    global LLM_INPUT_TOKENS, LLM_OUTPUT_TOKENS
    meta = resp.usage_metadata
    in_tok = int(meta.prompt_token_count or 0)
    out_tok = int(meta.candidates_token_count or 0)
    tot_tok = int(meta.total_token_count or (in_tok + out_tok))
    LLM_INPUT_TOKENS += in_tok
    LLM_OUTPUT_TOKENS += out_tok
    print(f"[TOKENS] {label}  prompt={in_tok}  output={out_tok}  total={tot_tok}")



def llm_generate_script(
    model: genai.GenerativeModel,
    description: str,
    examples_blob: str,
    bog_file_name: str,
    label: str = "generate",
) -> str:

    """
    Ask the LLM to emit a COMPLETE python script that, when run, writes a .bog.
    """
    global LLM_CALLS
    LLM_CALLS += 1
    REQUIRED_OUTPUT_FILE = f"{bog_file_name}.bog"


    prompt = f"""
You are an expert Niagara / HVAC controls code generator.

You will receive:
1) A brief description of the HVAC control sequence to build.
2) A bundle of example scripts that use BogFolderBuilder to create .bog files.

TASK: Produce ONE complete, runnable Python script that:
- Uses `from bog_builder import BogFolderBuilder` if installed OR falls back to local `src` layout:
    try:
        from bog_builder import BogFolderBuilder
    except ImportError:
        import sys, os
        sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))
        from bog_builder.builder import BogFolderBuilder
- Defines `main()` with argparse, supporting `-o/--output_dir` (default "examples")
- Builds the requested logic (based on the DESCRIPTION) using BogFolderBuilder APIs
  (add_numeric_writable, add_boolean_writable, add_component, add_link, start_sub_folder, end_sub_folder, etc.)
- Prints the absolute path to the created file.
- Avoids external network calls and third-party deps (standard lib only).
- Keep it deterministic (no random).
- Saves exactly one `.bog` file named REQUIRED_OUTPUT_FILE into `output_dir`.
- Prints the absolute path to REQUIRED_OUTPUT_FILE.


IMPORTANT:
- Follow the examples' conventions for linking (e.g., BooleanWritable uses "in16", NumericWritable often "in16" or appropriate slot).
- Prefer clear sub-folders for logic (e.g., "CalculationLogic").
- No commentary outside code. Return code only.

DESCRIPTION:
{description}

=== EXAMPLES (read-only reference) ===
{examples_blob}
"""
    resp = model.generate_content(prompt)
    _record_and_print_usage(resp, label=label)
    return _extract_python_code((resp.text or "").strip())


def llm_fix_script(
    model: genai.GenerativeModel,
    description: str,
    prev_code: str,
    error_text: str,
    examples_blob: str,
    bog_file_name: str,
    label: str = "fix",
) -> str:

    """
    Ask the LLM to REVISE the previous script based on traceback.
    """
    global LLM_CALLS
    LLM_CALLS += 1
    REQUIRED_OUTPUT_FILE = f"{bog_file_name}.bog"

    prompt = f"""
You previously generated a Python script to build a .bog from this description:

{description}

It FAILED to run with the following error/traceback (verbatim):
---
{error_text}
---

Here are the examples again (for reference):
{examples_blob}

Please return a FULLY CORRECTED script that fixes the error and still meets all requirements:
- Keep BogFolderBuilder usage.
- Keep `main()` with `-o/--output_dir`.
- Save exactly one `.bog` named {REQUIRED_OUTPUT_FILE} in the given output_dir and print its absolute path.
- No commentary outside code. Return code only.
"""
    resp = model.generate_content(prompt)
    _record_and_print_usage(resp, label=label)
    return _extract_python_code((resp.text or "").strip())


# ========= Synthesis loop =========

def write_script(code: str, path: Path) -> None:
    path.write_text(code, encoding="utf-8")
    # Make runnable
    try:
        path.chmod(0o755)
    except Exception:
        pass

def run_script(script_path: Path, out_dir: Path, timeout_sec: int = 120) -> Tuple[bool, str, str]:
    """
    Run a generated script. Returns (ok, stdout, stderr)
    """
    cmd = [sys.executable, str(script_path), "-o", str(out_dir)]
    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    try:
        stdout, stderr = proc.communicate(timeout=timeout_sec)
    except subprocess.TimeoutExpired:
        proc.kill()
        stdout, stderr = proc.communicate()
        stderr += "\n[TimeoutExpired]"
    ok = (proc.returncode == 0)
    return ok, stdout, stderr


# ========= CLI =========

def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        description="Synthesize a Python builder from natural language, run it, and iterate on errors."
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Final destination .bog file path. If omitted, will keep the name generated by the script in default folder."
    )
    parser.add_argument(
        "--max-iters",
        type=int,
        default=MAX_ITERS_DEFAULT,
        help=f"Max synthesize->run->fix attempts (default {MAX_ITERS_DEFAULT})."
    )
    parser.add_argument(
        "--workdir",
        default=".agent_tmp",
        help="Working directory to store synthesized scripts."
    )
    args = parser.parse_args(argv)

    model = init_gemini()
    if model is None:
        print("❌ Gemini unavailable.")
        return

    # Prompt user
    print(
        "Please describe the HVAC control system you wish to build.\n"
        "For example: 'Create a central plant with heating and cooling setpoints of 40°F/45°F and 75°F/70°F with a free cooling range between 50 and 60°F.'\n"
    )
    try:
        description = input("Description: ").strip()
    except EOFError:
        print("No description provided. Exiting.")
        return
    if not description:
        print("No description provided. Exiting.")
        return

    # Prompt user for bog file name
    print(
        "Please give a name for the bog file to generate.\n"
        "For example: 'central_plant_sequencing'\n"
    )
    try:
        bog_file_name = input("Bog File Name: ").strip()
    except EOFError:
        print("No bog file name provided. Exiting.")
        return
    if not bog_file_name:
        print("No bog file name provided. Exiting.")
        return

    # Prepare context & dirs
    examples_blob = gather_examples()
    workdir = Path(args.workdir); workdir.mkdir(parents=True, exist_ok=True)
    script_path = workdir / f"python_for_{bog_file_name}.py"
    out_dir = DEFAULT_OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    # Loop
    created_bog: Optional[Path] = None
    attempts = 0
    last_code = ""
    last_err = ""
    start_ts = time.time()

    while attempts < args.max_iters:
        attempts += 1
        print(f"\n--- Attempt {attempts}/{args.max_iters} ---")

        if attempts == 1:
            code = llm_generate_script(model, description, examples_blob, bog_file_name, label=f"generate (attempt {attempts})")

        else:
            code = llm_fix_script(model, description, last_code, last_err, examples_blob, bog_file_name)


        if not code.strip():
            print("❌ LLM returned empty code.")
            break

        write_script(code, script_path)
        ok, stdout, stderr = run_script(script_path, out_dir)
        last_code, last_err = code, (stderr or "")

        # Did a .bog land?
        candidate = out_dir / f"{bog_file_name}.bog"
        if ok and candidate.exists():
            created_bog = candidate
            print(stdout.strip() or f"Script reported success: {candidate}")
            break

        # Show brief error summary
        print("❌ Run failed. Traceback (tail):")
        tail = "\n".join((stderr or "").splitlines()[-30:])
        print(tail)

    # Finalize
    print("\n—— Stats ——")
    print(f"Gemini calls: {LLM_CALLS}")
    print(f"Attempts: {attempts}")
    print(f"Total input tokens: {LLM_INPUT_TOKENS}")
    print(f"Total output tokens: {LLM_OUTPUT_TOKENS}")
    print(f"Total tokens: {LLM_INPUT_TOKENS + LLM_OUTPUT_TOKENS}")


    if created_bog is None:
        print("❌ Failed to generate a working .bog.")
        return

    # Move/rename if --output was specified
    if args.output:
        dest = Path(args.output).expanduser().absolute()
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy2(created_bog, dest)
            print(f"✅ Generated .bog file at: {dest}")
        except Exception as e:
            print(f"⚠️ Could not move to requested output path ({e}). Keeping: {created_bog}")
            print(f"✅ Generated .bog file at: {created_bog}")
    else:
        print(f"✅ Generated .bog file at: {created_bog}")


if __name__ == "__main__":
    main()
