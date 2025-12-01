import yaml
import os
import time
import logging
import argparse
import asyncio
import json
import requests
import pandas as pd
from datetime import datetime, timedelta
import subprocess
import aiohttp

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("gke-generator")

SCENARIOS_FILE = os.getenv("SCENARIOS_FILE", "FAILURE_SCENARIOS.yaml")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "data/training_data")
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://localhost:9090")
LOKI_URL = os.getenv("LOKI_URL", "http://observability:3100")
TEMPO_URL = os.getenv("TEMPO_URL", "http://observability:3200")
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

async def generate_traffic(duration=60, rate=5):
    """Generates concurrent HTTP traffic to the simulation service."""
    url = f"http://sim-service.{NAMESPACE}.svc.cluster.local:8000/docs" # Simple endpoint
    logger.info(f"Starting traffic generator to {url} for {duration}s at ~{rate} req/s")
    
    start_time = time.time()
    async with aiohttp.ClientSession() as session:
        while time.time() - start_time < duration:
            tasks = []
            for _ in range(rate):
                tasks.append(session.get(url))
            
            try:
                responses = await asyncio.gather(*tasks, return_exceptions=True)
                # Optional: log success rate if needed
            except Exception as e:
                logger.warning(f"Traffic generation error: {e}")
            
            await asyncio.sleep(1) # 1 second batch

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

def query_loki_logs(namespace, start_time, end_time):
    """Query Loki for logs during scenario execution."""
    url = f"{LOKI_URL}/loki/api/v1/query_range"
    
    # Query for ALL logs in the namespace to ensure we see traffic
    query = f'{{namespace="{namespace}"}}'
    
    params = {
        "query": query,
        "start": int(start_time.timestamp() * 1e9),  # nanoseconds
        "end": int(end_time.timestamp() * 1e9),
        "limit": 1000
    }
    
    try:
        resp = requests.get(url, params=params, timeout=5)
        resp.raise_for_status()
        results = resp.json().get("data", {}).get("result", [])
    except Exception as e:
        logger.warning(f"Loki query failed: {e}")
        return {
            "log_total_count": 0, "log_error_count": 0, "log_exception_count": 0,
            "log_unique_errors": 0, "log_error_rate": 0.0,
            "log_error_samples": "[]", "log_warning_samples": "[]", "log_context": "[]"
        }
    
    # Extract log features
    log_features = {
        "total_logs": 0,
        "error_count": 0,
        "exception_count": 0,
        "unique_error_types": set(),
        "error_samples": [],
        "warning_samples": [],
        "context_samples": []
    }
    
    for stream in results:
        for entry in stream["values"]:
            timestamp, log_line = entry
            log_features["total_logs"] += 1
            
            log_lower = log_line.lower()
            if "error" in log_lower:
                log_features["error_count"] += 1
                if len(log_features["error_samples"]) < 5:
                    log_features["error_samples"].append(log_line[:200]) # Truncate
            elif "warn" in log_lower:
                if len(log_features["warning_samples"]) < 5:
                    log_features["warning_samples"].append(log_line[:200])
            else:
                if len(log_features["context_samples"]) < 5:
                    log_features["context_samples"].append(log_line[:200])

            if "exception" in log_lower or "traceback" in log_lower:
                log_features["exception_count"] += 1
                if ":" in log_line:
                    exc_type = log_line.split(":")[0].strip()
                    log_features["unique_error_types"].add(exc_type)
    
    return {
        "log_total_count": log_features["total_logs"],
        "log_error_count": log_features["error_count"],
        "log_exception_count": log_features["exception_count"],
        "log_unique_errors": len(log_features["unique_error_types"]),
        "log_error_rate": log_features["error_count"] / max(log_features["total_logs"], 1),
        "log_error_samples": json.dumps(log_features["error_samples"]),
        "log_warning_samples": json.dumps(log_features["warning_samples"]),
        "log_context": json.dumps(log_features["context_samples"])
    }

def query_tempo_traces(namespace, start_time, end_time):
    """Query Tempo for distributed traces."""
    url = f"{TEMPO_URL}/api/search"
    
    params = {
        "tags": "service.name=sim-service-agent",
        "start": int(start_time.timestamp()),
        "end": int(end_time.timestamp())
    }
    
    try:
        resp = requests.get(url, params=params, timeout=5)
        resp.raise_for_status()
        traces = resp.json().get("traces", [])
    except Exception as e:
        logger.warning(f"Tempo query failed: {e}")
        return {
            "trace_count": 0, "trace_span_count": 0, "trace_error_spans": 0,
            "trace_max_duration_ms": 0.0, "trace_avg_duration_ms": 0.0,
            "trace_p95_duration_ms": 0.0, "trace_error_rate": 0.0,
            "trace_slowest_json": "{}", "trace_error_json": "{}", "trace_dependencies": "[]"
        }
    
    trace_features = {
        "total_traces": len(traces),
        "span_count": 0,
        "error_spans": 0,
        "durations": [],
        "slowest_trace_id": None,
        "max_duration": -1,
        "error_trace_id": None
    }
    
    for trace in traces:
        trace_id = trace["traceID"]
        # In search results, we might not get full spans, but let's assume we get basic info
        # For full details we'd need to query each trace, but that's too slow.
        # We'll just query the slowest one and one error one.
        
        # Tempo search result usually has 'startTimeUnixNano' and 'durationMs'
        duration_ms = float(trace.get("durationMs", 0))
        trace_features["durations"].append(duration_ms)
        
        if duration_ms > trace_features["max_duration"]:
            trace_features["max_duration"] = duration_ms
            trace_features["slowest_trace_id"] = trace_id
            
        # Check for error tag if available in search results (often not, but let's try)
        # If not, we might skip detailed error check for all to save time, 
        # or just query details for the slowest one.
    
    # Calculate stats
    stats = {
        "trace_count": trace_features["total_traces"],
        "trace_span_count": 0, # Placeholder as we don't fetch all spans
        "trace_error_spans": 0,
        "trace_max_duration_ms": max(trace_features["durations"]) if trace_features["durations"] else 0,
        "trace_avg_duration_ms": sum(trace_features["durations"]) / len(trace_features["durations"]) if trace_features["durations"] else 0,
        "trace_p95_duration_ms": sorted(trace_features["durations"])[int(len(trace_features["durations"]) * 0.95)] if trace_features["durations"] else 0,
        "trace_error_rate": 0.0,
        "trace_slowest_json": "{}",
        "trace_error_json": "{}",
        "trace_dependencies": "[]"
    }

    # Fetch details for slowest trace
    if trace_features["slowest_trace_id"]:
        try:
            trace_url = f"{TEMPO_URL}/api/traces/{trace_features['slowest_trace_id']}"
            t_resp = requests.get(trace_url, timeout=2)
            if t_resp.status_code == 200:
                full_trace = t_resp.json()
                stats["trace_slowest_json"] = json.dumps(full_trace)[:5000] # Truncate
                
                # Extract dependencies
                services = set()
                for span in full_trace.get("spans", []):
                    stats["trace_span_count"] += 1
                    if "service.name" in span.get("attributes", {}): # OpenTelemetry convention
                         services.add(span["attributes"]["service.name"])
                    # Check for errors
                    if span.get("status", {}).get("code") == "STATUS_CODE_ERROR":
                         stats["trace_error_spans"] += 1
                
                stats["trace_dependencies"] = json.dumps(list(services))
        except Exception:
            pass

    return stats

async def collect_metrics(scenario, duration=60):
    logger.info(f"Collecting metrics, logs, and traces for {scenario['id']}...")
    
    start_time_collection = datetime.now()
    data_points = []
    
    # Start traffic generation in background
    traffic_task = asyncio.create_task(generate_traffic(duration=duration))
    
    # Collect for 'duration' seconds
    while (datetime.now() - start_time_collection).total_seconds() < duration:
        timestamp = datetime.now()
        
        # 1. Prometheus Metrics (existing)
        query = '{job=~"sim-.*|chaos-controller|kubelet-cadvisor|kube-state-metrics|node-exporter"}'
        try:
            response = requests.get(f"{PROMETHEUS_URL}/api/v1/query", params={'query': query}, timeout=5)
            response.raise_for_status()
            results = response.json()['data']['result']
        except Exception as e:
            logger.error(f"Prometheus query failed: {e}")
            results = []

        collected_metrics = {}
        ignored_labels = ['__name__', 'pod', 'instance', 'job', 'namespace', 'uid', 'container_id', 'image', 'id', 'endpoint', 'service']
        
        for result in results:
            metric_info = result['metric']
            name = metric_info.get('__name__', '')
            
            # Filter by namespace if possible, but bulk query gets everything. 
            # We should filter by the namespace we are targeting if the metric has it.
            # Many metrics don't have namespace, but job name often contains it (e.g. sim-api-15)
            # The current script runs in a specific namespace context? 
            # The NAMESPACE var is global.
            
            # Check if metric belongs to our namespace
            metric_ns = metric_info.get('namespace')
            metric_job = metric_info.get('job', '')
            
            # Heuristic: if namespace label exists, must match. If not, check job name.
            if metric_ns and metric_ns != NAMESPACE:
                continue
            if not metric_ns and NAMESPACE not in metric_job and "kube" not in metric_job and "node" not in metric_job:
                 # Keep node/kube metrics as they are shared, but maybe filter?
                 # For now, let's keep the logic simple as before.
                 pass

            labels = {k: v for k, v in metric_info.items() if k not in ignored_labels}
            if labels:
                label_str = "|".join([f"{k}={v}" for k, v in sorted(labels.items())])
                key = f"{name}|{label_str}"
            else:
                key = name
            
            try:
                collected_metrics[key] = float(result['value'][1])
            except (ValueError, IndexError):
                continue

        # 2. Loki Logs (NEW)
        # Increase lookback to 60s to account for ingestion lag
        log_features = query_loki_logs(NAMESPACE, timestamp - timedelta(seconds=60), timestamp)
        logger.info(f"Loki logs found: {log_features['log_total_count']}")
        
        # 3. Tempo Traces (NEW)
        trace_features = query_tempo_traces(NAMESPACE, timestamp - timedelta(seconds=60), timestamp)
        logger.info(f"Tempo traces found: {trace_features['trace_count']}")
        
        data_point = {
            "timestamp": timestamp.isoformat(),
            "scenario_id": scenario['id'],
            "label": scenario['root_cause'],
            **collected_metrics,
            **log_features,
            **trace_features
        }
        
        data_points.append(data_point)
        await asyncio.sleep(10)
    
    # Ensure traffic stops
    await traffic_task
    
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
    parser.add_argument("--prometheus-url", type=str, default=os.getenv("PROMETHEUS_URL", "http://observability:9090"), help="Prometheus URL") 
    args = parser.parse_args()
    
    global NAMESPACE, PROMETHEUS_URL, LOKI_URL, TEMPO_URL
    
    # Support for Kubernetes Indexed Jobs
    job_index = os.getenv("JOB_COMPLETION_INDEX")
    if job_index is not None:
        NAMESPACE = f"sim-api-{job_index}"
        logger.info(f"Running in Indexed Job mode. Target Namespace: {NAMESPACE}")
    else:
        NAMESPACE = args.namespace

    PROMETHEUS_URL = f"http://observability.{NAMESPACE}.svc.cluster.local:9090"
    LOKI_URL = f"http://observability.{NAMESPACE}.svc.cluster.local:3100"
    TEMPO_URL = f"http://observability.{NAMESPACE}.svc.cluster.local:3200"
    
    # Allow override if provided explicitly (e.g. for local testing)
    if args.prometheus_url != "http://observability:9090":
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
