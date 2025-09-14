import subprocess
import os
import sys
from datetime import datetime

# Paths
EXAMPLES_DIR = os.path.join(os.getcwd(), "examples")
# To this for WSL:
OUTPUT_DIR = "/mnt/c/Users/ben/Niagara4.13/JENEsys"

# The LOG_FILE line can remain the same, it will be created in your current directory
LOG_FILE = "/mnt/c/Users/ben/Niagara4.13/JENEsys/run_examples_log.txt"

STOP_ON_ERROR = True


def write_log(lines):
    """Helper function to write logs to the file."""
    with open(LOG_FILE, "a") as f:
        # Add a timestamp to each log session
        f.write(
            f"\n--- Log session: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n"
        )
        f.writelines(line + "\n" for line in lines)


def main():
    log_lines = []

    # Walk all subdirectories under EXAMPLES_DIR
    scripts = [
        os.path.relpath(
            os.path.join(root, f), start=os.getcwd()
        )  # relative to project root
        for root, _, files in os.walk(EXAMPLES_DIR)
        for f in files
        if f.endswith(".py")
    ]

    print(f"Found {len(scripts)} example scripts. Running them now...\n")

    for script_path in scripts:
        # Convert path to module notation (examples.simple_logic.addition_complicated)
        module_name = script_path[:-3].replace(
            os.sep, "."
        )  # strip ".py" and replace / with .

        cmd = [sys.executable, "-m", module_name, "-o", OUTPUT_DIR]

        log_lines.append(f"\n=== Running: {module_name} ===")
        print(f"[RUNNING] {module_name} -> Output: {OUTPUT_DIR}")

        try:
            # Key Change 1: Set check=True to automatically raise an error on failure
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            # This code will only be reached if the script runs successfully
            msg = f"[SUCCESS] {module_name}\n{result.stdout}"
            print(msg)
            log_lines.append(msg)

        # Key Change 2: Catch the specific error for a failed subprocess
        except subprocess.CalledProcessError as e:
            err = (
                f"[ERROR] {module_name} halted the execution.\n"
                f"Exit Code: {e.returncode}\n"
                f"--- STDERR ---\n{e.stderr}\n"
                f"--- STDOUT ---\n{e.stdout}"
            )
            print(err)
            log_lines.append(err)

            # Key Change 3: Write to log and exit immediately
            print("\nWriting logs and exiting due to error.")
            write_log(log_lines)
            if STOP_ON_ERROR:
                sys.exit(1)  # Exit with a non-zero status code to indicate failure

        except Exception as e:
            # This catches other errors, like the script not being found
            err_msg = f"[CRITICAL EXCEPTION] Could not run {module_name} -> {str(e)}"
            print(err_msg)
            log_lines.append(err_msg)
            print("\nWriting logs and exiting due to critical exception.")
            write_log(log_lines)
            if STOP_ON_ERROR:
                sys.exit(1)  # Exit with a non-zero status code to indicate failure

    # This part is only reached if all scripts succeed
    print("\nAll scripts completed successfully.")
    write_log(log_lines)


if __name__ == "__main__":
    main()
