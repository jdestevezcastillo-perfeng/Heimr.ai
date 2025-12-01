import subprocess
import time
import os
import signal
import sys

# Configuration
NUM_NAMESPACES = 20
BASE_NAMESPACE = "sim-api"
SCRIPT_PATH = "data-pipeline/run_gke_generation.py"
BUCKET_NAME = os.environ.get("BUCKET_NAME", "heimr-data-tokyo-snow-479722-a2")
# Use current python interpreter
VENV_PYTHON = sys.executable

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
    
    # Check if running in cluster
    in_cluster = os.environ.get("IN_CLUSTER", "false").lower() == "true"
    
    if in_cluster:
        print("Running in Kubernetes cluster mode.")
        # In-cluster URLs will be constructed dynamically per namespace
        # We don't set global URLs here because they differ per namespace
        pass
    else:
        print("Running in local mode.")
        # Explicitly set observability URLs to localhost for local execution
        env["PROMETHEUS_URL"] = "http://localhost:9090"
        env["LOKI_URL"] = "http://localhost:3100"
        env["TEMPO_URL"] = "http://localhost:3200"
        env["TARGET_URL"] = "http://localhost:8080/docs" # Traffic generator target

    for i in range(NUM_NAMESPACES):
        namespace = f"{BASE_NAMESPACE}-{i}"
        
        # Per-process environment
        proc_env = env.copy()
        
        if in_cluster:
            # Construct in-cluster DNS names
            # Service name assumption: observability-stack inside the namespace
            # Format: http://<service>.<namespace>.svc.cluster.local:<port>
            # Based on SYSTEM_MANIFEST, the pod is 'observability-stack'. 
            # We need to target the SERVICE. Assuming service name is 'observability-stack' or individual components.
            # Let's assume standard K8s DNS for the components if they are exposed as services.
            # If they are just pods, we might need a headless service or just target the pod IP if we knew it (hard).
            # BUT, usually we have services. Let's assume services named 'prometheus', 'loki', 'tempo' exist in the namespace.
            # Wait, SYSTEM_MANIFEST says "deployment_mode: Sidecar / Single Pod".
            # If it's a single pod named 'observability-stack', we need a Service to reach it.
            # Let's assume a service named 'observability-stack' exposes ports 9090, 3100, 3200.
            base_url = f"http://observability-stack.{namespace}.svc.cluster.local"
            proc_env["PROMETHEUS_URL"] = f"{base_url}:9090"
            proc_env["LOKI_URL"] = f"{base_url}:3100"
            proc_env["TEMPO_URL"] = f"{base_url}:3200"
            # Target URL for traffic gen (sim-service-agent)
            proc_env["TARGET_URL"] = f"http://sim-service-agent.{namespace}.svc.cluster.local:8000/docs"
        
        cmd = [
            VENV_PYTHON, 
            SCRIPT_PATH, 
            "--limit", "10000", 
            "--namespace", namespace
        ]
        
        print(f"Launching generator for {namespace}...")
        # Redirect stdout/stderr to separate log files to avoid console clutter
        # Redirect stdout/stderr to separate log files to avoid console clutter
        # In K8s, we might want to stream to stdout if we want to see logs in kubectl logs
        # But for 20 processes, that's messy. Let's keep file logging but maybe print a summary?
        # Actually, in K8s, writing to local files in the container is fine, but we lose them if pod restarts.
        # For now, let's keep it as is.
        os.makedirs("logs", exist_ok=True)
        with open(f"logs/gen_{namespace}.log", "w") as log_file:
            p = subprocess.Popen(cmd, env=proc_env, stdout=log_file, stderr=subprocess.STDOUT)
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
