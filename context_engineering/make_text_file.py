import os

# Paths
root_dir = r"C:\Users\ben\Documents\llm-bog-gen\examples"
output_file = r"C:\Users\ben\Documents\llm-bog-gen\context_engineering\llm_bog_instructions.txt"

with open(output_file, "a", encoding="utf-8") as out_f:  # append mode
    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.endswith(".py"):
                file_path = os.path.join(dirpath, filename)
                try:
                    with open(file_path, "r", encoding="utf-8") as py_f:
                        code = py_f.read()
                except Exception as e:
                    code = f"<<Error reading file: {e}>>"

                out_f.write(f"\n=== FILE: {filename} ===\n")
                print("Doing ",filename)
                out_f.write(f"DIR: {dirpath}\n")
                out_f.write("=== CODE START ===\n")
                out_f.write(code)
                out_f.write("\n=== CODE END ===\n")
                print("All Done...")
