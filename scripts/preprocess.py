# scripts/preprocess.py
import json
from pathlib import Path
from xml.sax.saxutils import escape

DATA_DIR = Path("../data")
PROMPTS_OUTPUTS = DATA_DIR / "prompts_outputs.jsonl"
SNIPPETS_DIR = DATA_DIR / "snippets"

# Sample prompt-output pair generator for fine-tuning dataset
def generate_prompt_output_pairs():
    examples = []
    for xml_file in SNIPPETS_DIR.glob("*.xml"):
        prompt_file = xml_file.with_suffix(".txt")
        if not prompt_file.exists():
            continue

        with open(prompt_file) as pf, open(xml_file) as xf:
            prompt = pf.read().strip()
            output = xf.read().strip()

            examples.append({
                "prompt": prompt,
                "completion": escape(output)  # escape for safety
            })

    PROMPTS_OUTPUTS.parent.mkdir(parents=True, exist_ok=True)
    with open(PROMPTS_OUTPUTS, "w") as f:
        for item in examples:
            f.write(json.dumps(item) + "\n")

    print(f"Wrote {len(examples)} prompt-output pairs to {PROMPTS_OUTPUTS}")


if __name__ == "__main__":
    generate_prompt_output_pairs()

