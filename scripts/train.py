
# scripts/train.py
from datasets import load_dataset
from transformers import AutoTokenizer, AutoModelForCausalLM, TrainingArguments, Trainer, DataCollatorForLanguageModeling
import torch
import os

MODEL_NAME = "gpt2"  # can change to code models like "Salesforce/codegen-350M-mono"
DATA_PATH = "../data/prompts_outputs.jsonl"


def tokenize_function(example):
    input_text = f"### Prompt:\n{example['prompt']}\n### Response:\n{example['completion']}"
    return tokenizer(input_text, truncation=True, padding="max_length", max_length=1024)


tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForCausalLM.from_pretrained(MODEL_NAME)

# Load and tokenize dataset
dataset = load_dataset("json", data_files=DATA_PATH, split="train")
tokenized_dataset = dataset.map(tokenize_function, batched=False)

# Training args
training_args = TrainingArguments(
    output_dir="../model",
    num_train_epochs=3,
    per_device_train_batch_size=2,
    save_steps=10,
    save_total_limit=2,
    logging_dir="../logs",
    logging_steps=5,
    fp16=torch.cuda.is_available(),
    remove_unused_columns=False,
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_dataset,
    tokenizer=tokenizer,
    data_collator=DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)
)

trainer.train()



