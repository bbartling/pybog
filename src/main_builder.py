from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

model_name = "bigcode/starcoder2-3b"

tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name)

device = torch.device("cpu")
model.to(device)

prompt = "Generate Niagara .bog XML logic for an AHU supply air reset with VAV demand input."

inputs = tokenizer(prompt, return_tensors="pt").to(device)
outputs = model.generate(**inputs, max_new_tokens=200)

print("\n=== Model Output ===\n")
print(tokenizer.decode(outputs[0], skip_special_tokens=True))
