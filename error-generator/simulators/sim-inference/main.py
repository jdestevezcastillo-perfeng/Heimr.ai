import asyncio
import logging
import os
import time
import threading
import random
import json
import sys
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, List
import torch

# OpenTelemetry imports
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource

# JSON Logging Formatter
class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_obj = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "namespace": os.getenv("NAMESPACE", "unknown"),
            "pod": os.getenv("HOSTNAME", "unknown"),
            "service": "sim-inference"
        }
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
            log_obj["error"] = True
        return json.dumps(log_obj)

# Configure JSON logging
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(JSONFormatter())
logging.root.handlers = []
logging.root.addHandler(handler)
logging.root.setLevel(logging.INFO)
logger = logging.getLogger("sim-inference")

# Configure OpenTelemetry
resource = Resource.create({
    "service.name": "sim-inference",
    "namespace": os.getenv("NAMESPACE", "unknown")
})
trace.set_tracer_provider(TracerProvider(resource=resource))
tracer = trace.get_tracer(__name__)

# Export to Tempo via OTLP
try:
    otlp_exporter = OTLPSpanExporter(
        endpoint="http://observability:4317",
        insecure=True
    )
    span_processor = BatchSpanProcessor(otlp_exporter)
    trace.get_tracer_provider().add_span_processor(span_processor)
    logger.info("OpenTelemetry tracing configured successfully")
except Exception as e:
    logger.warning(f"Failed to configure OpenTelemetry: {e}")

app = FastAPI(title="Heimr.ai Inference Simulator")

from prometheus_client import make_asgi_app, Gauge, Histogram, Counter
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# ========================================
# COMPREHENSIVE NVIDIA GPU METRICS
# ========================================

# --- DCGM Enterprise Metrics (H100 Style) ---
DCGM_TEMP = Gauge('DCGM_FI_DEV_GPU_TEMP', 'GPU temperature (C)', ['device', 'uuid'])
DCGM_POWER = Gauge('DCGM_FI_DEV_POWER_USAGE', 'Power usage (W)', ['device', 'uuid'])
DCGM_UTIL = Gauge('DCGM_FI_DEV_GPU_UTIL', 'GPU utilization (%)', ['device', 'uuid'])
DCGM_MEM_USED = Gauge('DCGM_FI_DEV_FB_USED', 'Framebuffer used (MiB)', ['device', 'uuid'])
DCGM_MEM_FREE = Gauge('DCGM_FI_DEV_FB_FREE', 'Framebuffer free (MiB)', ['device', 'uuid'])
DCGM_SM_CLOCK = Gauge('DCGM_FI_DEV_SM_CLOCK', 'SM clock (MHz)', ['device', 'uuid'])
DCGM_MEM_CLOCK = Gauge('DCGM_FI_DEV_MEM_CLOCK', 'Memory clock (MHz)', ['device', 'uuid'])

# --- Nvidia-SMI Consumer Metrics (Requested Style) ---
SMI_TEMP = Gauge('nvidia_smi_temperature_gpu', 'GPU temperature (C)', ['device', 'uuid'])
SMI_POWER = Gauge('nvidia_smi_power_draw_watts', 'Power draw (W)', ['device', 'uuid'])
SMI_UTIL = Gauge('nvidia_smi_utilization_gpu', 'GPU utilization (%)', ['device', 'uuid'])
SMI_MEM_USED = Gauge('nvidia_smi_memory_used_bytes', 'Memory used (Bytes)', ['device', 'uuid'])
SMI_MEM_FREE = Gauge('nvidia_smi_memory_free_bytes', 'Memory free (Bytes)', ['device', 'uuid'])
SMI_CLOCK_GRAPHICS = Gauge('nvidia_smi_clocks_graphics_mhz', 'Graphics clock (MHz)', ['device', 'uuid'])
SMI_CLOCK_MEM = Gauge('nvidia_smi_clocks_mem_mhz', 'Memory clock (MHz)', ['device', 'uuid'])

# --- Standard Exporter Metrics (Common) ---
GPU_UTIL_COMPUTE = Gauge('nvidia_gpu_utilization_compute', 'GPU compute utilization %', ['device', 'uuid'])
GPU_UTIL_MEMORY = Gauge('nvidia_gpu_utilization_memory', 'GPU memory controller utilization %', ['device', 'uuid'])
GPU_MEM_TOTAL = Gauge('nvidia_gpu_memory_total_bytes', 'Total GPU memory', ['device', 'uuid'])
GPU_MEM_USED = Gauge('nvidia_gpu_memory_used_bytes', 'Used GPU memory', ['device', 'uuid'])
GPU_MEM_FREE = Gauge('nvidia_gpu_memory_free_bytes', 'Free GPU memory', ['device', 'uuid'])
GPU_TEMP_GPU = Gauge('nvidia_gpu_temperature_celsius', 'GPU core temperature', ['device', 'uuid'])
GPU_POWER_DRAW = Gauge('nvidia_gpu_power_draw_watts', 'Current power draw', ['device', 'uuid'])
GPU_FAN_SPEED = Gauge('nvidia_gpu_fan_speed_percent', 'Fan speed %', ['device', 'uuid'])
GPU_PCIE_TX = Gauge('nvidia_gpu_pcie_tx_bytes_per_sec', 'PCIe TX throughput', ['device', 'uuid'])
GPU_PCIE_RX = Gauge('nvidia_gpu_pcie_rx_bytes_per_sec', 'PCIe RX throughput', ['device', 'uuid'])
GPU_NVLINK_BW = Gauge('nvidia_gpu_nvlink_bandwidth_bytes_per_sec', 'NVLink bandwidth', ['device', 'uuid'])
GPU_ECC_ERRORS = Counter('nvidia_gpu_ecc_errors_total', 'ECC errors', ['device', 'uuid', 'type'])

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
        logger.error(f"Compute load failed: {e}", exc_info=True)
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
        
        # --- Standard ---
        GPU_UTIL_COMPUTE.labels(device=DEVICE, uuid=GPU_UUID).set(min(100, state.util_compute))
        GPU_UTIL_MEMORY.labels(device=DEVICE, uuid=GPU_UUID).set(min(100, state.util_mem))
        # --- DCGM ---
        DCGM_UTIL.labels(device=DEVICE, uuid=GPU_UUID).set(min(100, state.util_compute))
        # --- SMI ---
        SMI_UTIL.labels(device=DEVICE, uuid=GPU_UUID).set(min(100, state.util_compute))
        
        # Memory Usage
        allocated_mb = 0
        if torch.cuda.is_available():
             allocated_mb = sum([t.element_size() * t.nelement() for t in state.allocated_tensors]) / (1024 * 1024)
        
        # Simulate model weights taking up memory (e.g., 40GB for large model)
        model_weights_mb = 40000 
        current_used_mb = model_weights_mb + allocated_mb + (load_factor * 5000) # Dynamic activation memory
        current_used_bytes = current_used_mb * 1024 * 1024
        total_bytes = TOTAL_MEM_MB * 1024 * 1024
        free_bytes = total_bytes - current_used_bytes
        
        # --- Standard ---
        GPU_MEM_TOTAL.labels(device=DEVICE, uuid=GPU_UUID).set(total_bytes)
        GPU_MEM_USED.labels(device=DEVICE, uuid=GPU_UUID).set(current_used_bytes)
        GPU_MEM_FREE.labels(device=DEVICE, uuid=GPU_UUID).set(free_bytes)
        # --- DCGM (MiB) ---
        DCGM_MEM_USED.labels(device=DEVICE, uuid=GPU_UUID).set(current_used_mb)
        DCGM_MEM_FREE.labels(device=DEVICE, uuid=GPU_UUID).set(TOTAL_MEM_MB - current_used_mb)
        # --- SMI (Bytes) ---
        SMI_MEM_USED.labels(device=DEVICE, uuid=GPU_UUID).set(current_used_bytes)
        SMI_MEM_FREE.labels(device=DEVICE, uuid=GPU_UUID).set(free_bytes)
        
        # Temperature (delayed reaction to load)
        target_temp = 35.0 + (load_factor * 50.0) # Max ~85C
        state.gpu_temp = state.gpu_temp * 0.9 + target_temp * 0.1
        
        # --- Standard ---
        GPU_TEMP_GPU.labels(device=DEVICE, uuid=GPU_UUID).set(state.gpu_temp)
        # --- DCGM ---
        DCGM_TEMP.labels(device=DEVICE, uuid=GPU_UUID).set(state.gpu_temp)
        # --- SMI ---
        SMI_TEMP.labels(device=DEVICE, uuid=GPU_UUID).set(state.gpu_temp)
        
        # Power
        target_power = 100.0 + (load_factor * 600.0) # Max 700W
        state.power_draw = state.power_draw * 0.8 + target_power * 0.2
        
        # --- Standard ---
        GPU_POWER_DRAW.labels(device=DEVICE, uuid=GPU_UUID).set(state.power_draw)
        # --- DCGM ---
        DCGM_POWER.labels(device=DEVICE, uuid=GPU_UUID).set(state.power_draw)
        # --- SMI ---
        SMI_POWER.labels(device=DEVICE, uuid=GPU_UUID).set(state.power_draw)
        
        # Fan Speed
        target_fan = max(30.0, (state.gpu_temp - 30.0) * 2.0)
        state.fan_speed = state.fan_speed * 0.9 + target_fan * 0.1
        GPU_FAN_SPEED.labels(device=DEVICE, uuid=GPU_UUID).set(min(100.0, state.fan_speed))
        
        # Clocks
        throttle_factor = 1.0
        if state.gpu_temp > 80.0:
            throttle_factor = 0.8
            
        graphics_clock = MAX_CLOCK_GRAPHICS * throttle_factor * random.uniform(0.95, 1.0)
        mem_clock = MAX_CLOCK_MEM * random.uniform(0.99, 1.0)
        
        # --- DCGM ---
        DCGM_SM_CLOCK.labels(device=DEVICE, uuid=GPU_UUID).set(graphics_clock)
        DCGM_MEM_CLOCK.labels(device=DEVICE, uuid=GPU_UUID).set(mem_clock)
        # --- SMI ---
        SMI_CLOCK_GRAPHICS.labels(device=DEVICE, uuid=GPU_UUID).set(graphics_clock)
        SMI_CLOCK_MEM.labels(device=DEVICE, uuid=GPU_UUID).set(mem_clock)
        
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
                logger.error(f"OOM during allocation: {e}", exc_info=True)
                
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
