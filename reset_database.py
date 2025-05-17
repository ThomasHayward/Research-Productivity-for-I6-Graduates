import os
import subprocess
import sys

base_dir = os.path.dirname(os.path.abspath(__file__))
clean_script = os.path.join(base_dir, 'python', 'cleaning', 'deep_clean_database.py')
init_script = os.path.join(base_dir, 'python', 'initialize_database.py')

def run_script(script_path):
    result = subprocess.run([sys.executable, script_path])
    if result.returncode != 0:
        print(f"Error running {script_path}")
        sys.exit(result.returncode)

if __name__ == "__main__":
    run_script(clean_script)
    run_script(init_script)
