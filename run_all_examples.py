import subprocess
import os
import sys
from datetime import datetime

# Paths
EXAMPLES_DIR = os.path.join(os.getcwd(), "examples")
OUTPUT_DIR = r"C:\Users\ben\Niagara4.11\JENEsys"  # Change if needed
LOG_FILE = "run_examples_log.txt"


def main():
    log_lines = []

    # Walk all subdirectories under EXAMPLES_DIR
    scripts = [
        os.path.relpath(os.path.join(root, f), start=os.getcwd())  # relative to project root
        for root, _, files in os.walk(EXAMPLES_DIR)
        for f in files if f.endswith(".py")
    ]

    print(f"Found {len(scripts)} example scripts. Running them now...\n")

    for script_path in scripts:
        # Convert path to module notation (examples.simple_logic.addition_complicated)
        module_name = script_path[:-3].replace(os.sep, ".")  # strip ".py" and replace / with .

        cmd = [sys.executable, "-m", module_name, "-o", OUTPUT_DIR]

        log_lines.append(f"\n=== Running: {module_name} ===\n")
        print(f"[RUNNING] {module_name} -> Output: {OUTPUT_DIR}")

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if result.returncode == 0:
                msg = f"[SUCCESS] {module_name}\n{result.stdout}"
                print(msg)
                log_lines.append(msg)
            else:
                err = (
                    f"[ERROR] {module_name}\nExit Code: {result.returncode}\n{result.stderr}"
                )
                print(err)
                log_lines.append(err)

        except Exception as e:
            err_msg = f"[EXCEPTION] {module_name} -> {str(e)}"
            print(err_msg)
            log_lines.append(err_msg)

    # Write log file (optional)
    """
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_path = os.path.join(os.getcwd(), f"logs_{timestamp}.txt")
    with open(log_path, "w") as log_file:
        log_file.writelines(line + "\n" for line in log_lines)

    print(f"\n=== All examples processed. Logs saved to: {log_path} ===")
    """


if __name__ == "__main__":
    main()
