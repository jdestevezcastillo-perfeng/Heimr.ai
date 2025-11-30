import yaml
import os
import time
import logging
import argparse
import asyncio
import json
import requests
import pandas as pd
from datetime import datetime
import subprocess

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("gke-generator")

SCENARIOS_FILE = os.getenv("SCENARIOS_FILE", "docs/data/failure_scenarios.yaml")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "data/training_data")
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://localhost:9090")
NAMESPACE = "sim-api"

async def run_command(cmd):
    process = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    if process.returncode != 0:
        logger.error(f"Command failed: {cmd}\nStderr: {stderr.decode()}")
        return False
    return True

async def inject_fault(scenario):
    """Applies the ChaosScenario CRD to the existing namespace."""
    logger.info(f"Injecting fault for {scenario['id']} in {NAMESPACE}")
    
    # Map scenario to ChaosScenario spec (simplified logic)
    action = "latency"
    config = {"latency_ms": "500"} # Ensure string for some fields if needed, but CRD expects int/string depending on def
    target = {"labelSelector": "app=sim-service-agent"} # Default target
    
    name = scenario['name'].lower()
    
    if "cpu" in name or "resource" in name:
        action = "cpu-burn"
        config = {"load": "80"}
    elif "memory" in name or "leak" in name:
        action = "memory-leak"
    elif "database" in name:
        action = "lock-table"
        target = {"labelSelector": "app=sim-db"}
    elif "cache" in name:
        action = "flush-redis"
        target = {"labelSelector": "app=sim-cache"}
    elif "gpu" in name:
        action = "compute-load"
        target = {"labelSelector": "app=sim-inference"}
        
    crd = {
        "apiVersion": "heimr.ai/v1",
        "kind": "ChaosScenario",
        "metadata": {"name": f"chaos-{scenario['id'].lower().replace('_', '-')}", "namespace": NAMESPACE},
        "spec": {
            "target": target,
            "action": action,
            "config": config,
            "duration": "60s"
        }
    }
    
    crd_file = f"/tmp/crd-{scenario['id']}.yaml"
    with open(crd_file, "w") as f:
        yaml.dump(crd, f)
        
    # Use full path to kubectl if needed, or assume it's in PATH (we exported it in previous steps)
    # But for python subprocess, we might need to be careful. 
    # We'll assume kubectl is in PATH or use the one we configured.
    cmd = f"kubectl apply -f {crd_file}"
    return await run_command(cmd)

async def delete_fault(scenario):
    name = f"chaos-{scenario['id'].lower().replace('_', '-')}"
    cmd = f"kubectl delete chaosscenario {name} -n {NAMESPACE} --ignore-not-found"
    await run_command(cmd)

def query_prometheus(query):
    try:
        response = requests.get(f"{PROMETHEUS_URL}/api/v1/query", params={'query': query})
        response.raise_for_status()
        results = response.json()['data']['result']
        if results:
            return float(results[0]['value'][1])
        return 0.0
    except Exception as e:
        logger.error(f"Prometheus query failed: {e}")
        return 0.0

async def collect_metrics(scenario, duration=60):
    logger.info(f"Collecting metrics for {scenario['id']}...")
    
    # Wait for chaos to manifest
    # We can poll every 10s
    start_time = time.time()
    data_points = []
    
    while time.time() - start_time < duration:
        timestamp = datetime.now().isoformat()
        
        # Query key metrics
        # Adjust queries based on your actual metric names
        latency = query_prometheus('rate(http_request_duration_seconds_sum[1m]) / rate(http_request_duration_seconds_count[1m])')
        error_rate = query_prometheus('rate(http_requests_total{status=~"5.."}[1m]) / rate(http_requests_total[1m])')
        cpu_usage = query_prometheus('sum(rate(container_cpu_usage_seconds_total{namespace="sim-api"}[1m]))')
        
        data_point = {
            "timestamp": timestamp,
            "scenario_id": scenario['id'],
            "label": scenario['root_cause'], # Target label
            "latency": latency,
            "error_rate": error_rate,
            "cpu_usage": cpu_usage
        }
        data_points.append(data_point)
        await asyncio.sleep(10)
        
    return data_points

async def process_scenario(scenario):
    try:
        await inject_fault(scenario)
        data = await collect_metrics(scenario)
        await delete_fault(scenario)
        return data
    except Exception as e:
        logger.error(f"Error processing {scenario['id']}: {e}")
        await delete_fault(scenario) # Ensure cleanup
        return []

from google.cloud import storage

# ... (existing imports)

BUCKET_NAME = os.getenv("BUCKET_NAME")

def upload_to_gcs(file_path, destination_blob_name):
    """Uploads a file to the bucket."""
    if not BUCKET_NAME:
        logger.warning("BUCKET_NAME not set, skipping GCS upload.")
        return

    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(destination_blob_name)
        blob.upload_from_filename(file_path)
        logger.info(f"File {file_path} uploaded to {destination_blob_name}.")
    except Exception as e:
        logger.error(f"Failed to upload to GCS: {e}")

async def main():
    parser = argparse.ArgumentParser(description="GKE Data Generator")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of scenarios")
    parser.add_argument("--namespace", type=str, default="sim-api", help="Target Kubernetes namespace")
    # Default to internal DNS for in-cluster execution
    parser.add_argument("--prometheus-url", type=str, default="http://observability:9090", help="Prometheus URL") 
    args = parser.parse_args()
    
    global NAMESPACE, PROMETHEUS_URL
    NAMESPACE = args.namespace
    PROMETHEUS_URL = args.prometheus_url
    
    with open(SCENARIOS_FILE, "r") as f:
        scenarios = yaml.safe_load(f)
        
    if args.limit > 0:
        scenarios = scenarios[:args.limit]
        
    logger.info(f"Loaded {len(scenarios)} scenarios. Target: {NAMESPACE}, Prometheus: {PROMETHEUS_URL}")
    
    all_data = []
    
    # Run sequentially for now to avoid chaos interference
    for s in scenarios:
        data = await process_scenario(s)
        all_data.extend(data)
        
    # Save to Parquet
    if all_data:
        df = pd.DataFrame(all_data)
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        filename = f"gke_{NAMESPACE}_{int(time.time())}.parquet"
        output_file = f"{OUTPUT_DIR}/{filename}"
        df.to_parquet(output_file)
        logger.info(f"Saved {len(df)} rows to {output_file}")
        
        # Upload to GCS
        upload_to_gcs(output_file, filename)
    else:
        logger.warning("No data collected.")

if __name__ == "__main__":
    asyncio.run(main())
