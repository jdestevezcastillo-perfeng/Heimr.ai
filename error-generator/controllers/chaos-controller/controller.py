import kopf
import kubernetes
import logging
import random
import time
import asyncio
import aiohttp
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("chaos-controller")

@kopf.on.startup()
def configure(settings: kopf.OperatorSettings, **_):
    settings.posting.level = logging.INFO

@kopf.on.create('heimr.ai', 'v1', 'chaosscenarios')
async def create_fn(spec, name, namespace, **kwargs):
    """
    Triggered when a ChaosScenario CRD is created.
    """
    logger.info(f"Chaos Scenario {name} started in {namespace}")
    
    target = spec.get('target', {})
    action = spec.get('action')
    config = spec.get('config', {}) # e.g., { "latency_ms": 500 }
    duration = spec.get('duration', '10s')
    
    api = kubernetes.client.CoreV1Api()
    
    try:
        if action == 'pod-delete':
            delete_pods(api, namespace, target)
        elif action in ['latency', 'cpu-burn', 'memory-leak', 'error-injection', 'connection-leak', 'lock-table', 'flush-redis', 'kafka-flood', 'compute-load', 'vram-fill']:
            await inject_application_fault(api, namespace, target, action, config)
        else:
            raise kopf.PermanentError(f"Unknown action: {action}")
            
        return {'status': 'executed', 'action': action}
        
    except Exception as e:
        logger.error(f"Chaos failed: {e}")
        raise kopf.TemporaryError(f"Chaos failed: {str(e)}", delay=5)

def delete_pods(api, namespace, target):
    label_selector = target.get('labelSelector')
    if not label_selector:
        raise kopf.PermanentError("Target must have labelSelector")
        
    pods = api.list_namespaced_pod(namespace, label_selector=label_selector)
    if not pods.items:
        logger.info("No pods found matching selector")
        return

    # Pick a random victim
    victim = random.choice(pods.items)
    logger.info(f"Deleting pod {victim.metadata.name}")
    
    api.delete_namespaced_pod(
        name=victim.metadata.name,
        namespace=namespace
    )

async def inject_application_fault(api, namespace, target, action, config):
    """
    Finds target pods and calls their sidecar API to inject faults.
    """
    label_selector = target.get('labelSelector')
    if not label_selector:
        raise kopf.PermanentError("Target must have labelSelector")
        
    pods = api.list_namespaced_pod(namespace, label_selector=label_selector)
    if not pods.items:
        logger.info("No pods found matching selector")
        return

    # Map actions to sidecar config keys
    payload = {}
    if action == 'latency':
        payload = {"latency_ms": config.get('latency_ms', 100), "latency_jitter_ms": config.get('jitter_ms', 0)}
    elif action == 'cpu-burn':
        payload = {"cpu_burn_ms": config.get('duration_ms', 1000), "cpu_burn": True}
    elif action == 'memory-leak':
        payload = {"memory_leak_bytes": config.get('bytes', 1048576)}
    elif action == 'error-injection':
        payload = {"error_rate": config.get('rate', 1.0)}
    elif action == 'connection-leak':
        payload = {"connection_leak_count": config.get('count', 10)}
    elif action == 'lock-table':
        payload = {"lock_table": config.get('table', 'users')}
    elif action == 'flush-redis':
        payload = {"flush_all": True}
    elif action == 'kafka-flood':
        payload = {"flood_messages_per_sec": config.get('rate', 100)}
    elif action == 'compute-load':
        payload = {"compute_load": True}
    elif action == 'vram-fill':
        payload = {"allocate_vram_mb": config.get('mb', 1000)}
    
    # Send to all matching pods (or random subset if specified)
    async with aiohttp.ClientSession() as session:
        tasks = []
        for pod in pods.items:
            pod_ip = pod.status.pod_ip
            if not pod_ip: continue
            
            url = f"http://{pod_ip}:8000/control/chaos"
            logger.info(f"Injecting {action} into {pod.metadata.name} ({url})")
            tasks.append(session.post(url, json=payload))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for res in results:
            if isinstance(res, Exception):
                logger.error(f"Failed to inject fault: {res}")

@kopf.on.delete('heimr.ai', 'v1', 'chaosscenarios')
async def delete_fn(spec, name, namespace, **kwargs):
    """
    Reset chaos when the CRD is deleted.
    """
    logger.info(f"Chaos Scenario {name} deleted - Resetting targets")
    target = spec.get('target', {})
    api = kubernetes.client.CoreV1Api()
    
    label_selector = target.get('labelSelector')
    if not label_selector: return

    pods = api.list_namespaced_pod(namespace, label_selector=label_selector)
    if not pods.items: return

    async with aiohttp.ClientSession() as session:
        tasks = []
        for pod in pods.items:
            pod_ip = pod.status.pod_ip
            if not pod_ip: continue
            url = f"http://{pod_ip}:8000/control/reset"
            tasks.append(session.post(url))
        
        await asyncio.gather(*tasks, return_exceptions=True)
