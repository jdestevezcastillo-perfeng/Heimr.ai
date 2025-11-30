import asyncio
import logging
import os
import time
import threading
import random
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, List
import torch

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("sim-inference")

app = FastAPI(title="Heimr.ai Inference Simulator")

from prometheus_client import make_asgi_app, Gauge, Histogram, Counter
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# ========================================
# COMPREHENSIVE NVIDIA GPU METRICS
# ========================================

# GPU Utilization
GPU_UTIL_COMPUTE = Gauge('nvidia_gpu_utilization_compute', 'GPU compute utilization %', ['device', 'uuid'])
GPU_UTIL_MEMORY = Gauge('nvidia_gpu_utilization_memory', 'GPU memory controller utilization %', ['device', 'uuid'])

# Memory Metrics
GPU_MEM_TOTAL = Gauge('nvidia_gpu_memory_total_bytes', 'Total GPU memory', ['device', 'uuid'])
GPU_MEM_USED = Gauge('nvidia_gpu_memory_used_bytes', 'Used GPU memory', ['device', 'uuid'])
GPU_MEM_FREE = Gauge('nvidia_gpu_memory_free_bytes', 'Free GPU memory', ['device', 'uuid'])
GPU_MEM_RESERVED = Gauge('nvidia_gpu_memory_reserved_bytes', 'Reserved GPU memory', ['device', 'uuid'])

# Temperature & Power
GPU_TEMP_GPU = Gauge('nvidia_gpu_temperature_celsius', 'GPU core temperature', ['device', 'uuid'])
GPU_TEMP_MEM = Gauge('nvidia_gpu_temperature_memory_celsius', 'GPU memory temperature', ['device', 'uuid'])
GPU_POWER_DRAW = Gauge('nvidia_gpu_power_draw_watts', 'Current power draw', ['device', 'uuid'])
GPU_POWER_LIMIT = Gauge('nvidia_gpu_power_limit_watts', 'Power limit', ['device', 'uuid'])
GPU_FAN_SPEED = Gauge('nvidia_gpu_fan_speed_percent', 'Fan speed %', ['device', 'uuid'])

# Clocks
GPU_CLOCK_GRAPHICS = Gauge('nvidia_gpu_clock_graphics_mhz', 'Graphics clock speed', ['device', 'uuid'])
GPU_CLOCK_SM = Gauge('nvidia_gpu_clock_sm_mhz', 'SM clock speed', ['device', 'uuid'])
GPU_CLOCK_MEM = Gauge('nvidia_gpu_clock_mem_mhz', 'Memory clock speed', ['device', 'uuid'])

# PCIe & NVLink
GPU_PCIE_TX = Gauge('nvidia_gpu_pcie_tx_bytes_per_sec', 'PCIe TX throughput', ['device', 'uuid'])
GPU_PCIE_RX = Gauge('nvidia_gpu_pcie_rx_bytes_per_sec', 'PCIe RX throughput', ['device', 'uuid'])
GPU_NVLINK_BW = Gauge('nvidia_gpu_nvlink_bandwidth_bytes_per_sec', 'NVLink bandwidth', ['device', 'uuid'])

# Health
GPU_ECC_ERRORS = Counter('nvidia_gpu_ecc_errors_total', 'ECC errors', ['device', 'uuid', 'type']) # type: volatile/aggregate
GPU_THROTTLED = Gauge('nvidia_gpu_throttled', '1 if throttled (thermal/power)', ['device', 'uuid'])

# ========================================
# INFERENCE METRICS
# ========================================
INFERENCE_LATENCY = Histogram('inference_latency_seconds', 'Time spent processing inference', ['model'])
INFERENCE_REQUESTS = Counter('inference_requests_total', 'Total inference requests', ['model', 'status'])
INFERENCE_BATCH_SIZE = Histogram('inference_batch_size', 'Batch size distribution', ['model'])
INFERENCE_TOKENS_PER_SEC = Gauge('inference_tokens_per_second', 'Throughput in tokens/sec', ['model'])
INFERENCE_QUEUE_DEPTH = Gauge('inference_queue_depth', 'Pending requests in queue', ['model'])
INFERENCE_ACTIVE_REQUESTS = Gauge('inference_active_requests', 'Currently processing requests', ['model'])


# Device Detection
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
GPU_UUID = f"GPU-{os.urandom(4).hex()}-{os.urandom(2).hex()}-{os.urandom(2).hex()}-{os.urandom(6).hex()}"
logger.info(f"Running on device: {DEVICE} ({GPU_UUID})")

class ChaosState:
    allocated_tensors: List[torch.Tensor] = []
    compute_load_active: bool = False
    compute_thread = None
    inference_latency_ms: int = 50 # Baseline latency
    inference_jitter_ms: int = 10
    # Simulated state
    gpu_temp = 35.0
    mem_temp = 30.0
    power_draw = 100.0
    fan_speed = 30.0
    util_compute = 0.0
    util_mem = 0.0

state = ChaosState()

class ChaosConfig(BaseModel):
    allocate_vram_mb: Optional[int] = 0
    compute_load: Optional[bool] = False
    inference_latency_ms: Optional[int] = None

def compute_load_task():
    """Performs matrix multiplications to heat up GPU/CPU."""
    logger.info(f"Starting compute load on {DEVICE}...")
    try:
        # Create two random matrices
        size = 2048 
        if DEVICE == "cuda":
            a = torch.randn(size, size, device=DEVICE)
            b = torch.randn(size, size, device=DEVICE)
        else:
            # Smaller for CPU to avoid freezing
            size = 512
            a = torch.randn(size, size)
            b = torch.randn(size, size)
        
        while state.compute_load_active:
            _ = torch.matmul(a, b)
            time.sleep(0.001) 
    except Exception as e:
        logger.error(f"Compute load failed: {e}")
    finally:
        logger.info("Stopped compute load.")

async def simulate_gpu_activity():
    """Background task that generates realistic NVIDIA GPU metrics (H100 specs)"""
    logger.info("Starting GPU activity simulation...")
    
    # H100 Specs
    TOTAL_MEM_MB = 81920 # 80GB
    POWER_LIMIT_W = 700.0
    MAX_CLOCK_GRAPHICS = 1980
    MAX_CLOCK_MEM = 1593
    
    while True:
        # Determine load factor based on chaos + random noise
        base_load = 0.8 if state.compute_load_active else 0.1
        load_factor = min(1.0, max(0.0, random.gauss(base_load, 0.05)))
        
        # Update Utilization
        target_util = load_factor * 100
        state.util_compute = state.util_compute * 0.8 + target_util * 0.2 # Smooth transition
        state.util_mem = state.util_compute * random.uniform(0.8, 1.1)
        
        GPU_UTIL_COMPUTE.labels(device=DEVICE, uuid=GPU_UUID).set(min(100, state.util_compute))
        GPU_UTIL_MEMORY.labels(device=DEVICE, uuid=GPU_UUID).set(min(100, state.util_mem))
        
        # Memory Usage
        # Base usage + allocated tensors + random fluctuation
        allocated_mb = 0
        if torch.cuda.is_available():
             allocated_mb = sum([t.element_size() * t.nelement() for t in state.allocated_tensors]) / (1024 * 1024)
        
        # Simulate model weights taking up memory (e.g., 40GB for large model)
        model_weights_mb = 40000 
        current_used_mb = model_weights_mb + allocated_mb + (load_factor * 5000) # Dynamic activation memory
        
        GPU_MEM_TOTAL.labels(device=DEVICE, uuid=GPU_UUID).set(TOTAL_MEM_MB * 1024 * 1024)
        GPU_MEM_USED.labels(device=DEVICE, uuid=GPU_UUID).set(current_used_mb * 1024 * 1024)
        GPU_MEM_FREE.labels(device=DEVICE, uuid=GPU_UUID).set((TOTAL_MEM_MB - current_used_mb) * 1024 * 1024)
        
        # Temperature (delayed reaction to load)
        target_temp = 35.0 + (load_factor * 50.0) # Max ~85C
        state.gpu_temp = state.gpu_temp * 0.9 + target_temp * 0.1
        state.mem_temp = state.gpu_temp * 0.95 # Slightly cooler
        
        GPU_TEMP_GPU.labels(device=DEVICE, uuid=GPU_UUID).set(state.gpu_temp)
        GPU_TEMP_MEM.labels(device=DEVICE, uuid=GPU_UUID).set(state.mem_temp)
        
        # Power
        target_power = 100.0 + (load_factor * 600.0) # Max 700W
        state.power_draw = state.power_draw * 0.8 + target_power * 0.2
        
        GPU_POWER_DRAW.labels(device=DEVICE, uuid=GPU_UUID).set(state.power_draw)
        GPU_POWER_LIMIT.labels(device=DEVICE, uuid=GPU_UUID).set(POWER_LIMIT_W)
        
        # Fan Speed (reactive to temp)
        target_fan = max(30.0, (state.gpu_temp - 30.0) * 2.0)
        state.fan_speed = state.fan_speed * 0.9 + target_fan * 0.1
        GPU_FAN_SPEED.labels(device=DEVICE, uuid=GPU_UUID).set(min(100.0, state.fan_speed))
        
        # Clocks (throttle if hot)
        throttle_factor = 1.0
        if state.gpu_temp > 80.0:
            throttle_factor = 0.8
            GPU_THROTTLED.labels(device=DEVICE, uuid=GPU_UUID).set(1)
        else:
            GPU_THROTTLED.labels(device=DEVICE, uuid=GPU_UUID).set(0)
            
        GPU_CLOCK_GRAPHICS.labels(device=DEVICE, uuid=GPU_UUID).set(MAX_CLOCK_GRAPHICS * throttle_factor * random.uniform(0.95, 1.0))
        GPU_CLOCK_SM.labels(device=DEVICE, uuid=GPU_UUID).set(MAX_CLOCK_GRAPHICS * throttle_factor * random.uniform(0.95, 1.0))
        GPU_CLOCK_MEM.labels(device=DEVICE, uuid=GPU_UUID).set(MAX_CLOCK_MEM * random.uniform(0.99, 1.0))
        
        # PCIe & NVLink
        pcie_activity = load_factor * 1024 * 1024 * 1024 * 10 # Up to 10 GB/s
        GPU_PCIE_TX.labels(device=DEVICE, uuid=GPU_UUID).set(pcie_activity * random.uniform(0.8, 1.2))
        GPU_PCIE_RX.labels(device=DEVICE, uuid=GPU_UUID).set(pcie_activity * random.uniform(0.1, 0.3))
        
        nvlink_activity = load_factor * 1024 * 1024 * 1024 * 50 # Up to 50 GB/s
        GPU_NVLINK_BW.labels(device=DEVICE, uuid=GPU_UUID).set(nvlink_activity)
        
        # ECC Errors (rare)
        if random.random() < 0.0001:
            GPU_ECC_ERRORS.labels(device=DEVICE, uuid=GPU_UUID, type='volatile').inc()
            
        # Inference specific metrics simulation
        if load_factor > 0.2:
            INFERENCE_TOKENS_PER_SEC.labels(model="sim-model-7b").set(random.randint(50, 150))
            INFERENCE_QUEUE_DEPTH.labels(model="sim-model-7b").set(random.randint(0, 10))
            INFERENCE_ACTIVE_REQUESTS.labels(model="sim-model-7b").set(random.randint(1, 5))
        else:
            INFERENCE_TOKENS_PER_SEC.labels(model="sim-model-7b").set(0)
            INFERENCE_QUEUE_DEPTH.labels(model="sim-model-7b").set(0)
            INFERENCE_ACTIVE_REQUESTS.labels(model="sim-model-7b").set(0)

        await asyncio.sleep(0.5)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(simulate_gpu_activity())

@app.post("/control/chaos")
async def set_chaos(config: ChaosConfig):
    """Inject Inference faults."""
    
    # VRAM/RAM Saturation
    if config.allocate_vram_mb is not None:
        current_mb = sum([t.element_size() * t.nelement() for t in state.allocated_tensors]) / (1024 * 1024)
        target_mb = config.allocate_vram_mb
        
        if target_mb > current_mb:
            needed_mb = target_mb - current_mb
            # Allocate in 100MB chunks
            chunk_size_mb = 100
            chunks = int(needed_mb / chunk_size_mb)
            remainder_mb = needed_mb % chunk_size_mb
            
            try:
                # 100MB float32 tensor = 25M elements * 4 bytes
                elements_per_chunk = int((chunk_size_mb * 1024 * 1024) / 4)
                
                for _ in range(chunks):
                    if DEVICE == "cuda":
                        t = torch.empty(elements_per_chunk, dtype=torch.float32, device=DEVICE)
                    else:
                        t = torch.empty(elements_per_chunk, dtype=torch.float32)
                    state.allocated_tensors.append(t)
                
                if remainder_mb > 0:
                    elements = int((remainder_mb * 1024 * 1024) / 4)
                    if DEVICE == "cuda":
                        t = torch.empty(elements, dtype=torch.float32, device=DEVICE)
                    else:
                        t = torch.empty(elements, dtype=torch.float32)
                    state.allocated_tensors.append(t)
                    
                logger.info(f"Allocated additional {needed_mb}MB on {DEVICE}")
            except RuntimeError as e:
                logger.error(f"OOM during allocation: {e}")
                
        elif target_mb < current_mb:
            # Deallocate
            state.allocated_tensors.clear()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            logger.info("Cleared allocated memory")

    # Compute Load
    if config.compute_load is not None:
        if config.compute_load and not state.compute_load_active:
            state.compute_load_active = True
            state.compute_thread = threading.Thread(target=compute_load_task)
            state.compute_thread.start()
        elif not config.compute_load and state.compute_load_active:
            state.compute_load_active = False
            if state.compute_thread:
                state.compute_thread.join()

    # Latency Injection
    if config.inference_latency_ms is not None:
        state.inference_latency_ms = config.inference_latency_ms

    return {"status": "updated", "device": DEVICE, "state": {
        "allocated_tensors_count": len(state.allocated_tensors),
        "compute_load": state.compute_load_active,
        "latency_ms": state.inference_latency_ms
    }}

@app.post("/control/reset")
async def reset_chaos():
    state.allocated_tensors.clear()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    
    state.compute_load_active = False
    if state.compute_thread: state.compute_thread.join()
    
    state.inference_latency_ms = 50
    return {"status": "reset"}

@app.post("/v1/chat/completions")
async def mock_inference():
    """Simulates an LLM inference endpoint."""
    start_time = time.time()
    INFERENCE_REQUESTS.labels(model="sim-model-7b", status="processing").inc()
    
    # Simulate processing time
    delay = state.inference_latency_ms + random.randint(0, state.inference_jitter_ms)
    await asyncio.sleep(delay / 1000.0)
    
    duration = time.time() - start_time
    INFERENCE_LATENCY.labels(model="sim-model-7b").observe(duration)
    INFERENCE_REQUESTS.labels(model="sim-model-7b", status="success").inc()
    INFERENCE_BATCH_SIZE.labels(model="sim-model-7b").observe(1) # Simulating batch size 1 for now
    
    return {
        "id": "chatcmpl-mock",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": "sim-model-7b",
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "This is a simulated response from the chaos inference engine."
            },
            "finish_reason": "stop"
        }],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30
        }
    }

@app.get("/health")
async def health():
    return {"status": "healthy", "device": DEVICE}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
