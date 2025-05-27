# llm-bog-gen
Experimental train or fine-tune a language model (LLM) to generate .bog XML wire sheet logic from natural-language prompts like:  "Make me AHU duct static pressure reset to all my VAV boxes in the BACnet driver."  And have it output the correct .bog XML or Java code blocks embedded in .bog files.


* ***AI fine-tuning project that outputs Niagara `.bog` wire sheet logic**. Let’s walk through how to set this up:

## On Windows how to find saved models downloaded from Huggingface
The `main.py` automatically downloads model and then saves in a cache location.

```bash
Get-ChildItem -Recurse "$env:USERPROFILE\.cache\huggingface" -Directory
```
That will output:
```bash
C:\Users\ben\.cache\huggingface\hub
```

---

## ✅ Goal

Train or fine-tune a language model (LLM) to **generate `.bog` XML wire sheet logic** from natural-language prompts like:

> "Make me AHU duct static pressure reset to all my VAV boxes in the BACnet driver."

And have it output the correct `.bog` XML or Java code blocks embedded in `.bog` files.

---

## 🔧 What You’ll Need

### 1. **Corpus of Q\&A Examples**

Start collecting your own dataset of:

* Natural language **prompts** (the kind a controls tech would type)
* Target **output snippets** (actual `.bog` XML or logic blocks)

Example JSON format:

```json
{
  "prompt": "Create AHU duct static pressure reset for 20 VAV boxes.",
  "output": "<bajaObjectGraph>...</bajaObjectGraph>"
}
```

Start small. Even **100–200** good pairs will be enough for initial training via adapters or fine-tuning.

### 2. **Preprocessing and Escaping XML**

Make sure the `.bog` XML is:

* **Escaped** or pre-tokenized safely
* Possibly broken into **code chunks**, depending on the training method (more on this below)

You can either:

* Escape all special characters (`&lt;`, `&#xa;`, etc.)
* Or use a **code-friendly tokenizer** (e.g., from Hugging Face) that preserves XML structure

---

## 🧠 Which Model to Fine-Tune?

Start with a small language model:

* `CodeLlama`, `Phi-2`, `Mistral`, `StarCoder`, or `TinyLlama` if you want **open-source**
* Or use **OpenAI’s fine-tuning endpoint** (GPT-3.5 Turbo) with a curated dataset

**Note**: GPT models don’t support XML structure enforcement — if you want stronger XML fidelity, fine-tune something like `StarCoderBase` with Hugging Face.

---

## 🛠️ Tooling Stack

| Task             | Tool                                                                |
| ---------------- | ------------------------------------------------------------------- |
| Dataset prep     | Python or Pandas                                                    |
| Fine-tuning      | Hugging Face (`transformers` + `peft`) or OpenAI CLI                |
| Model hosting    | Local with `text-generation-webui` or cloud via Replicate/HF Spaces |
| Prompt interface | Jupyter notebook, Streamlit, or CLI script                          |

---

## 📁 Project Layout

```
llm-bog-gen/
├── data/
│   ├── prompts_outputs.jsonl     # Training pairs
│   └── snippets/                 # Saved bog file snippets
├── scripts/
│   ├── preprocess.py             # Convert BOG XMLs to training format
│   └── train.py                  # Fine-tuning script
├── model/                        # Fine-tuned model artifacts
└── README.md                     # Dev notes and tutorial
```

---

## 🚀 Example Prompt Engineering Strategy

| Prompt                                                     | Output                       |
| ---------------------------------------------------------- | ---------------------------- |
| “Make a trim and respond AHU SAT reset block for 10 VAVs.” | Java logic + `.bog` block    |
| “Create BACnet points and wiring for chilled water reset”  | Full block with `Link` nodes |
| “Use G36 rules to generate discharge air temp reset”       | Annotated wire sheet XML     |

---

## 🧪 Bonus Ideas

* Use **semantic search** to match prompts to existing `.bog` templates
* Embed and vectorize wire sheet logic with `sentence-transformers`
* Add a **Brick or Haystack tag parser** to auto-generate points

---

## Why Escape XML for GPT Fine-Tuning?

GPT models (like GPT-3.5 or GPT-4) do not natively parse or enforce **structured XML grammar**. They treat XML as plain text, which makes them flexible but error-prone for outputting deeply nested structures like `.bog` files.

To reduce syntax breakage and ensure well-formed outputs:
- We **escape XML** (`<` becomes `&lt;`, etc.)
- You can **post-process the output** back into raw XML after generation
- For stricter control, consider training on **code-friendly tokenizers** (like CodeLlama or StarCoder) instead of GPT

If your target is Niagara `.bog` generation, you'll want the model to **learn how to structure blocks, slots, and links correctly**, even if it's only partially complete and human-assisted afterward.


---

## 📍 License

This project is open source and made available under the permissive [MIT License](LICENSE), allowing for reuse, modification, and distribution with attribution.

Built with ❤️ and iterative guidance from [ChatGPT](https://openai.com/chatgpt) — including this README, modeling code, and data prep structure — as part of a research-driven exploration for the HVAC industry of the future.