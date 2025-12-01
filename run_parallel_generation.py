import subprocess
import time
import os
import signal
import sys

# Configuration
NUM_NAMESPACES = 20
BASE_NAMESPACE = "sim-api"
SCRIPT_PATH = "data-pipeline/run_gke_generation.py"
BUCKET_NAME = "heimr-data-tokyo-snow-479722-a2"
VENV_PYTHON = "/home/lostborion/Heimr.ai/.venv/bin/python"

processes = []

def signal_handler(sig, frame):
    print("\nStopping all generation processes...")
    for p in processes:
        p.terminate()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

def run_parallel():
    print(f"Starting parallel data generation for {NUM_NAMESPACES} namespaces...")
    
    env = os.environ.copy()
    env["BUCKET_NAME"] = BUCKET_NAME
    # Explicitly set observability URLs to localhost for local execution
    env["PROMETHEUS_URL"] = "http://localhost:9090"
    env["LOKI_URL"] = "http://localhost:3100"
    env["TEMPO_URL"] = "http://localhost:3200"
    env["TARGET_URL"] = "http://localhost:8080/docs" # Traffic generator target
    
    for i in range(NUM_NAMESPACES):
        namespace = f"{BASE_NAMESPACE}-{i}"
        cmd = [
            VENV_PYTHON, 
            SCRIPT_PATH, 
            "--limit", "10000", 
            "--namespace", namespace
        ]
        
        print(f"Launching generator for {namespace}...")
        # Redirect stdout/stderr to separate log files to avoid console clutter
        with open(f"logs/gen_{namespace}.log", "w") as log_file:
            p = subprocess.Popen(cmd, env=env, stdout=log_file, stderr=subprocess.STDOUT)
            processes.append(p)
            
    print(f"All {len(processes)} processes started. Logs in logs/gen_sim-api-*.log")
    print("Press Ctrl+C to stop.")
    
    # Monitor processes
    while True:
        all_done = True
        for p in processes:
            if p.poll() is None:
                all_done = False
                break
        
        if all_done:
            print("All generation processes completed.")
            break
            
        time.sleep(5)

if __name__ == "__main__":
    os.makedirs("logs", exist_ok=True)
    run_parallel()
