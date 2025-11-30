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
    if "healthy" in scenario['name'].lower():
        logger.info(f"Skipping fault injection for healthy scenario: {scenario['id']}")
        return True

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
        
        # Query ALL metrics for the namespace (Bulk Ingestion)
        # We fetch everything matching the relevant jobs to capture Postgres, Redis, Kafka, GPU, etc.
        # Note: App metrics don't have 'namespace' label, so we query by job name.
        query = '{job=~"sim-.*|chaos-controller|kubelet-cadvisor|kube-state-metrics|node-exporter"}'
        
        try:
            response = requests.get(f"{PROMETHEUS_URL}/api/v1/query", params={'query': query})
            response.raise_for_status()
            results = response.json()['data']['result']
        except Exception as e:
            logger.error(f"Prometheus query failed: {e}")
            results = []

        collected_metrics = {}
        for result in results:
            metric_info = result['metric']
            name = metric_info.get('__name__')
            if not name: continue
            
            # Filter out high-cardinality/unstable labels to ensure consistent Parquet schema
            # We drop 'pod', 'instance', 'uid', etc. so columns don't change on every restart
            ignored_labels = ['__name__', 'pod', 'instance', 'job', 'namespace', 'uid', 'container_id', 'image', 'id', 'endpoint', 'service']
            labels = {k: v for k, v in metric_info.items() if k not in ignored_labels}
            
            # Construct flat column name: metric_name|label1=val1|label2=val2
            if labels:
                # Sort labels for deterministic naming
                label_str = "|".join([f"{k}={v}" for k, v in sorted(labels.items())])
                key = f"{name}|{label_str}"
            else:
                key = name
                
            try:
                collected_metrics[key] = float(result['value'][1])
            except (ValueError, IndexError):
                continue
        
        logger.info(f"Collected {len(collected_metrics)} metrics for {scenario['id']}")

        data_point = {
            "timestamp": timestamp,
            "scenario_id": scenario['id'],
            "label": scenario['root_cause'],
            **collected_metrics
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
    
    # Balance the dataset: Interleave "Healthy Baseline" (API-001) with failure scenarios
    # This ensures a ~50/50 ratio, which is ideal for training (vs the current 1/50 ratio).
    healthy_scenario = next((s for s in scenarios if s['id'] == 'API-001'), None)
    
    if healthy_scenario:
        failure_scenarios = [s for s in scenarios if s['id'] != 'API-001']
        balanced_scenarios = []
        for failure in failure_scenarios:
            # Add healthy sample before every failure
            balanced_scenarios.append(healthy_scenario)
            balanced_scenarios.append(failure)
        scenarios = balanced_scenarios
        logger.info(f"Balanced dataset enabled: {len(scenarios)} total runs (50% Healthy).")
    else:
        logger.warning("Healthy Baseline (API-001) not found! Running unbalanced.")

    all_data = []
    
    # Run sequentially for now to avoid chaos interference
    for s in scenarios:
        data = await process_scenario(s)
        if data:
            df = pd.DataFrame(data)
            os.makedirs(OUTPUT_DIR, exist_ok=True)
            filename = f"gke_{NAMESPACE}_{s['id']}_{int(time.time())}.parquet"
            output_file = f"{OUTPUT_DIR}/{filename}"
            df.to_parquet(output_file)
            logger.info(f"Saved {len(df)} rows to {output_file}")
            
            # Upload to GCS
            upload_to_gcs(output_file, filename)
        else:
            logger.warning(f"No data collected for {s['id']}")

if __name__ == "__main__":
    asyncio.run(main())
