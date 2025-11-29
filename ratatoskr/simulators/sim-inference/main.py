import asyncio
import logging
import os
import time
import threading
import random
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import torch

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("sim-inference")

app = FastAPI(title="Heimr.ai Inference Simulator")

# Device Detection
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
logger.info(f"Running on device: {DEVICE}")

class ChaosState:
    allocated_tensors: List[torch.Tensor] = []
    compute_load_active: bool = False
    compute_thread = None
    inference_latency_ms: int = 50 # Baseline latency
    inference_jitter_ms: int = 10

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
        size = 2048 # Adjust based on desired load intensity
        a = torch.randn(size, size, device=DEVICE)
        b = torch.randn(size, size, device=DEVICE)
        
        while state.compute_load_active:
            # Matrix multiplication is compute heavy
            _ = torch.matmul(a, b)
            # Small sleep to prevent complete lockup if single threaded
            time.sleep(0.001) 
    except Exception as e:
        logger.error(f"Compute load failed: {e}")
    finally:
        logger.info("Stopped compute load.")

@app.post("/control/chaos")
async def set_chaos(config: ChaosConfig):
    """Inject Inference faults."""
    
    # 1. VRAM/RAM Saturation
    if config.allocate_vram_mb is not None:
        current_mb = sum([t.element_size() * t.nelement() for t in state.allocated_tensors]) / (1024 * 1024)
        target_mb = config.allocate_vram_mb
        
        if target_mb > current_mb:
            needed_mb = target_mb - current_mb
            # Allocate in 100MB chunks to avoid fragmentation failure on single large alloc
            chunk_size_mb = 100
            chunks = int(needed_mb / chunk_size_mb)
            remainder_mb = needed_mb % chunk_size_mb
            
            try:
                # 100MB float32 tensor = 25M elements * 4 bytes
                elements_per_chunk = int((chunk_size_mb * 1024 * 1024) / 4)
                
                for _ in range(chunks):
                    t = torch.empty(elements_per_chunk, dtype=torch.float32, device=DEVICE)
                    state.allocated_tensors.append(t)
                
                if remainder_mb > 0:
                    elements = int((remainder_mb * 1024 * 1024) / 4)
                    t = torch.empty(elements, dtype=torch.float32, device=DEVICE)
                    state.allocated_tensors.append(t)
                    
                logger.info(f"Allocated additional {needed_mb}MB on {DEVICE}")
            except RuntimeError as e:
                logger.error(f"OOM during allocation: {e}")
                # Don't raise 500, just report what we managed
                
        elif target_mb < current_mb:
            # Deallocate
            state.allocated_tensors.clear()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            logger.info("Cleared allocated memory")

    # 2. Compute Load (Thermal Throttling Simulation)
    if config.compute_load is not None:
        if config.compute_load and not state.compute_load_active:
            state.compute_load_active = True
            state.compute_thread = threading.Thread(target=compute_load_task)
            state.compute_thread.start()
        elif not config.compute_load and state.compute_load_active:
            state.compute_load_active = False
            if state.compute_thread:
                state.compute_thread.join()

    # 3. Latency Injection
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
    # Simulate processing time
    delay = state.inference_latency_ms + random.randint(0, state.inference_jitter_ms)
    
    # If compute load is high, real latency might naturally increase, 
    # but we add artificial delay to control it precisely.
    await asyncio.sleep(delay / 1000.0)
    
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
