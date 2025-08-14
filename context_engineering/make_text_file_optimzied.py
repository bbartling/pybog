"""
make_text_file_optimized.py

Usage (example):
    python make_text_file_optimized.py --backup BACKUP_llm_bog_instructions.txt \
        --root C:\\Users\\ben\\Documents\\llm-bog-gen\\examples \
        --out llm_bog_instructions_token_optimized.txt

If --root is omitted or not found, only the BACKUP is optimized.

BALANCED
py .\make_text_file_optimized.py `
  --backup .\BACKUP_llm_bog_instructions.txt `
  --root C:\Users\ben\Documents\llm-bog-gen\examples `
  --out .\llm_bog_instructions_token_optimized.txt `
  --mode balanced

AGRESSIVE
py .\make_text_file_optimized.py `
  --backup .\BACKUP_llm_bog_instructions.txt `
  --root C:\Users\ben\Documents\llm-bog-instructions\examples `
  --out .\llm_bog_instructions_token_optimized_aggr.txt `
  --mode aggressive

BACKUP ONLY
py .\make_text_file_optimized.py `
  --backup .\BACKUP_llm_bog_instructions.txt `
  --out .\llm_bog_instructions_token_optimized.txt

"""

import argparse
from pathlib import Path
import re
import math
import ast
import json

def approx_tokens(s: str) -> int:
    # Rough heuristic: 1 token ~ 4 chars
    return (len(s) + 3) // 4

# ---------- Python code summarizer/minifier ----------
def strip_python_comments_and_blank_lines(src: str) -> str:
    out_lines = []
    for line in src.splitlines():
        # Drop full-line comments; keep code (naive: does not remove inline '#')
        if line.strip().startswith("#"):
            continue
        out_lines.append(line.rstrip())
    # Collapse multiple blank lines
    collapsed = []
    blank = 0
    for ln in out_lines:
        if ln.strip() == "":
            blank += 1
            if blank <= 1:
                collapsed.append("")
        else:
            blank = 0
            collapsed.append(ln)
    return "\n".join(collapsed).strip() + "\n"

def extract_signatures(src: str) -> str:
    """Return a short summary of classes/defs with arg names only (no bodies)."""
    try:
        tree = ast.parse(src)
    except Exception:
        return ""
    sig_lines = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            args = [a.arg for a in node.args.args]
            sig_lines.append(f"def {node.name}({', '.join(args)}): ...")
        elif isinstance(node, ast.AsyncFunctionDef):
            args = [a.arg for a in node.args.args]
            sig_lines.append(f"async def {node.name}({', '.join(args)}): ...")
        elif isinstance(node, ast.ClassDef):
            sig_lines.append(f"class {node.name}: ...")
    return "\n".join(sig_lines)

# ---------- Heuristic optimizer for the BACKUP/context ----------
MODAL_RE = re.compile(r"\b(MUST|SHOULD|NEVER|ALWAYS|REQUIRED|PROHIBITED|MUST NOT|SHALL|SHALL NOT)\b", re.I)
KEYWORDS = [
    "Niagara", "kitControl", "bog", "WsAnnotation", "builder", "add_component", "add_link",
    "slot", "handle", "folder", "subfolder", "layout", "wsAnnotation",
    "Tridium", "Program Object", "NumericWritable", "BooleanWritable", "GreaterThan", "Switch",
    "compare", "math", "timer", "delay", "ms", "n4", "kitControl:", "b:WsAnnotation",
    "module", "palette", "link", "target", "source", "inA", "inB", "out", "coords",
    "reset", "counter", "naming rules", "naming conventions",
    "precision", "defaultValue", "properties", "hysteresis", "Mode",
    "HeatSP", "CoolSP", "Fan", "Output_", "Logic", "TopLimit", "LowLimit", "Step"
]

def keep_line(s: str) -> bool:
    if not s.strip():
        return True
    if MODAL_RE.search(s):
        return True
    if any(k in s for k in KEYWORDS):
        return True
    # short bullets/headings
    if s.lstrip().startswith(("#","-","*")) and len(s) < 220:
        return True
    # explicit constraint verbs
    if re.search(r"\b(use|avoid|prefer|forbid|ensure|exact|format|return only|tagged|naming)\b", s, re.I) and len(s) < 240:
        return True
    # very long lines likely examples -> drop unless key terms matched above
    if len(s) > 300:
        return False
    if 40 <= len(s) <= 220 and s.strip().endswith((".", ":", ";")):
        return True
    return False

def optimize_text(raw: str) -> str:
    lines = raw.splitlines()
    kept = [ln for ln in lines if keep_line(ln)]
    # dedupe in order
    seen = set()
    dedup = []
    for ln in kept:
        key = ln.strip()
        if key not in seen:
            dedup.append(ln)
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
            collapsed.append(ln.rstrip())
    return ("\n".join(collapsed)).strip() + "\n"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backup", required=True, help="Path to BACKUP text file to optimize")
    ap.add_argument("--root", default="", help="Optional root dir containing .py examples to summarize")
    ap.add_argument("--out", required=True, help="Output optimized text file")
    ap.add_argument("--mode", choices=["aggressive","balanced"], default="balanced",
                    help="Aggressive keeps fewer lines from BACKUP; balanced keeps more rules")
    args = ap.parse_args()

    backup_path = Path(args.backup)
    out_path = Path(args.out)
    root_dir = Path(args.root) if args.root else None

    raw_backup = backup_path.read_text(encoding="utf-8", errors="ignore")

    # Optionally tighten the heuristic slightly if aggressive
    global KEYWORDS
    if args.mode == "aggressive":
        KEYWORDS = [k for k in KEYWORDS if k not in {"TopLimit","LowLimit","Step"}]

    # 1) Optimize the BACKUP text
    optimized_backup = optimize_text(raw_backup)

    # 2) Optionally summarize Python files
    py_summary_chunks = []
    if root_dir and root_dir.exists():
        for p in sorted(root_dir.rglob("*.py")):
            try:
                src = p.read_text(encoding="utf-8", errors="ignore")
            except Exception as e:
                src = f"<<Error reading {p}: {e}>>"
            signatures = extract_signatures(src)
            minified = strip_python_comments_and_blank_lines(src)
            short_preview = minified[:1200]  # tighten this (e.g., 600) to save more tokens
            chunk = (
                f"=== PY SUMMARY: {p.name} ===\n"
                f"{signatures}\n\n"
                f"=== PY PREVIEW (minified): ===\n"
                f"{short_preview}\n"
            )
            py_summary_chunks.append(chunk)

    combined = optimized_backup
    if py_summary_chunks:
        combined += "\n\n# ===== PY FILE SUMMARIES (token-light) =====\n" + "\n".join(py_summary_chunks)

    out_path.write_text(combined, encoding="utf-8")

    report = {
        "backup_chars": len(raw_backup),
        "optimized_chars": len(combined),
        "backup_est_tokens": approx_tokens(raw_backup),
        "optimized_est_tokens": approx_tokens(combined),
        "reduction_percent_chars": round((1 - len(combined)/len(raw_backup)) * 100, 2) if len(raw_backup) else 0.0,
        "out_path": str(out_path),
    }
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
