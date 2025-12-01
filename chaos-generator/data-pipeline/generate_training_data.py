import yaml
import os
import time
import subprocess
import logging
import argparse
import asyncio
import json
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("data-generator")

SCENARIOS_FILE = os.getenv("SCENARIOS_FILE", "FAILURE_SCENARIOS.yaml")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "data/training_data")
HELM_CHART = os.getenv("HELM_CHART", "chaos-generator/charts/simulation-topology")

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

async def deploy_scenario(scenario, namespace):
    """Deploys a scenario topology using Helm."""
    logger.info(f"Deploying scenario {scenario['id']} to {namespace}")
    
    # 1. Determine Topology based on 'affected_systems'
    # This is a simplified mapping logic
    values = {
        "services": [],
        "databases": [],
        "caches": [],
        "queues": [],
        "inference": []
    }
    
    systems = scenario.get('affected_systems', [])
    
    # Always have at least one service
    values["services"].append({"name": "frontend", "env": {"SCENARIO_ID": scenario['id']}})
    
    if "Database" in systems:
        values["databases"].append({"name": "primary-db"})
        values["services"][0]["env"]["DB_HOST"] = "primary-db"
        
    if "Caching" in systems:
        values["caches"].append({"name": "redis-cache"})
        
    if "Event-Driven" in systems or "Messaging" in systems:
        values["queues"].append({"name": "kafka-cluster"})
        
    if "AI/ML Inference" in systems or "GPU" in systems:
        values["inference"].append({"name": "llm-worker", "gpu": True})

    # 2. Write temporary values file
    values_file = f"/tmp/values-{namespace}.yaml"
    with open(values_file, "w") as f:
        yaml.dump(values, f)
        
    # 3. Helm Install
    cmd = f"helm upgrade --install {namespace} {HELM_CHART} --namespace {namespace} --create-namespace -f {values_file} --wait"
    return await run_command(cmd)

async def inject_fault(scenario, namespace):
    """Applies the ChaosScenario CRD."""
    logger.info(f"Injecting fault for {scenario['id']} in {namespace}")
    
    # Map scenario to ChaosScenario spec
    # This requires parsing the 'root_cause' or 'description' to determine action
    # For prototype, we default to 'latency' if not obvious
    
    action = "latency"
    config = {"latency_ms": 500}
    target = {"labelSelector": "app=frontend"}
    
    name = scenario['name'].lower()
    
    if "CPU" in name or "Resource" in name:
        action = "cpu-burn"
    elif "Memory" in name or "Leak" in name:
        action = "memory-leak"
    elif "Database" in name:
        action = "lock-table"
        target = {"labelSelector": "app=primary-db"}
    elif "Cache" in name:
        action = "flush-redis"
        target = {"labelSelector": "app=redis-cache"}
        
    crd = {
        "apiVersion": "heimr.ai/v1",
        "kind": "ChaosScenario",
        "metadata": {"name": f"chaos-{scenario['id'].lower()}", "namespace": namespace},
        "spec": {
            "target": target,
            "action": action,
            "config": config,
            "duration": "60s"
        }
    }
    
    crd_file = f"/tmp/crd-{namespace}.yaml"
    with open(crd_file, "w") as f:
        yaml.dump(crd, f)
        
    cmd = f"kubectl apply -f {crd_file}"
    return await run_command(cmd)

async def collect_metrics(scenario, namespace, duration=60):
    """
    Simulates metric collection. 
    In prod, this would query Prometheus.
    """
    logger.info(f"Collecting metrics for {scenario['id']}...")
    await asyncio.sleep(duration) # Wait for chaos to manifest
    
    # Mock Data Saving
    data_point = {
        "timestamp": datetime.now().isoformat(),
        "scenario_id": scenario['id'],
        "metrics": {
            "latency_p99": 500 + (os.getpid() % 100), # Random-ish
            "error_rate": 0.05
        },
        "label": scenario['root_cause']
    }
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(f"{OUTPUT_DIR}/{scenario['id']}.json", "a") as f:
        f.write(json.dumps(data_point) + "\n")

async def cleanup(namespace):
    cmd = f"helm uninstall {namespace} -n {namespace} && kubectl delete namespace {namespace}"
    await run_command(cmd)

async def process_scenario(scenario, semaphore):
    async with semaphore:
        namespace = f"sim-{scenario['id'].lower().replace('_', '-')}"
        try:
            if await deploy_scenario(scenario, namespace):
                await inject_fault(scenario, namespace)
                await collect_metrics(scenario, namespace)
        finally:
            await cleanup(namespace)

async def main():
    parser = argparse.ArgumentParser(description="Parallel Data Generator")
    parser.add_argument("--parallelism", type=int, default=5, help="Number of parallel scenarios")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of scenarios to run")
    args = parser.parse_args()
    
    with open(SCENARIOS_FILE, "r") as f:
        scenarios = yaml.safe_load(f)
        
    if args.limit > 0:
        scenarios = scenarios[:args.limit]
        
    logger.info(f"Loaded {len(scenarios)} scenarios. Running with parallelism={args.parallelism}")
    
    semaphore = asyncio.Semaphore(args.parallelism)
    tasks = [process_scenario(s, semaphore) for s in scenarios]
    
    await asyncio.gather(*tasks)
    logger.info("Data generation complete.")

if __name__ == "__main__":
    asyncio.run(main())
