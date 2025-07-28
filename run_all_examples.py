import subprocess
import os
import sys
from datetime import datetime

# Paths
EXAMPLES_DIR = os.path.join(os.getcwd(), "examples")
OUTPUT_DIR = r"C:\Users\ben\Niagara4.11\JENEsys"  # Change if needed
LOG_FILE = "run_examples_log.txt"


def main():
    examples = [f for f in os.listdir(EXAMPLES_DIR) if f.endswith(".py")]
    log_lines = []

    print(f"Found {len(examples)} example scripts. Running them now...\n")

    for script in examples:
        script_path = os.path.join(EXAMPLES_DIR, script)
        cmd = [sys.executable, script_path, "-o", OUTPUT_DIR]

        log_lines.append(f"\n=== Running: {script} ===\n")
        print(f"[RUNNING] {script} -> Output: {OUTPUT_DIR}")

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if result.returncode == 0:
                msg = f"[SUCCESS] {script}\n{result.stdout}"
                print(msg)
                log_lines.append(msg)
            else:
                err = (
                    f"[ERROR] {script}\nExit Code: {result.returncode}\n{result.stderr}"
                )
                print(err)
                log_lines.append(err)

        except Exception as e:
            err_msg = f"[EXCEPTION] {script} -> {str(e)}"
            print(err_msg)
            log_lines.append(err_msg)

    # Write log file

    """
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_path = os.path.join(os.getcwd(), f"logs_{timestamp}.txt")
    with open(log_path, "w") as log_file:
        log_file.writelines(line + "\n" for line in log_lines)

    print(f"\n=== All examples processed. Logs saved to: {log_path} ===")
    """


if __name__ == "__main__":
    main()
