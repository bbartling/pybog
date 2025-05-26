from transformers import AutoTokenizer, AutoModelForCausalLM

# Choose a lightweight CPU-friendly model
model_name = "sshleifer/tiny-gpt2"  # or "distilgpt2", etc.

# Download and cache model + tokenizer
print(f"📦 Downloading model: {model_name}")
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name)

print("✅ Model and tokenizer downloaded and cached.")
