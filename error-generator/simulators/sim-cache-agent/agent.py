import asyncio
import logging
import os
import redis
import threading
import time
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("sim-cache-agent")

app = FastAPI(title="Heimr.ai Cache Chaos Agent")

# Redis Config
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))

class ChaosState:
    active_connections: List[any] = []
    memory_fill_active: bool = False
    memory_fill_thread = None
    cpu_burn_active: bool = False
    cpu_burn_thread = None

state = ChaosState()

class ChaosConfig(BaseModel):
    flush_all: Optional[bool] = False
    connection_leak_count: Optional[int] = 0
    fill_memory_mb: Optional[int] = 0
    cpu_burn: Optional[bool] = False

def get_redis_connection():
    try:
        return redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        return None

def fill_memory_task(target_mb):
    """Fills Redis memory with junk data."""
    logger.info(f"Starting memory fill target={target_mb}MB...")
    r = get_redis_connection()
    if not r: return

    chunk_size = 1024 * 1024 # 1MB
    key_prefix = "chaos:memfill:"
    count = 0
    
    try:
        while state.memory_fill_active and count < target_mb:
            # Write 1MB chunk
            r.set(f"{key_prefix}{count}", "X" * chunk_size)
            count += 1
            time.sleep(0.1) # Prevent total lockup
    except Exception as e:
        logger.error(f"Memory fill failed: {e}")
    finally:
        logger.info(f"Stopped memory fill. Added {count}MB.")

def cpu_burn_task():
    """Spikes Redis CPU by running expensive commands."""
    logger.info("Starting CPU burn (KEYS * loop)...")
    r = get_redis_connection()
    if not r: return

    try:
        while state.cpu_burn_active:
            # KEYS * is O(N) and blocks the main thread
            r.keys("*")
            time.sleep(0.01)
    except Exception as e:
        logger.error(f"CPU burn failed: {e}")
    finally:
        logger.info("Stopped CPU burn.")

@app.post("/control/chaos")
async def set_chaos(config: ChaosConfig):
    """Inject Cache faults."""
    
    # 1. Cache Stampede (Flush All)
    if config.flush_all:
        r = get_redis_connection()
        if r:
            r.flushall()
            logger.info("Executed FLUSHALL")
        else:
            raise HTTPException(status_code=500, detail="Could not connect to Redis")

    # 2. Connection Leak
    if config.connection_leak_count is not None:
        current_count = len(state.active_connections)
        target_count = config.connection_leak_count
        
        if target_count > current_count:
            for _ in range(target_count - current_count):
                r = get_redis_connection()
                if r:
                    # Ping to establish connection
                    r.ping()
                    state.active_connections.append(r)
            logger.info(f"Leaked connections: {len(state.active_connections)}")
        elif target_count < current_count:
            to_remove = current_count - target_count
            for _ in range(to_remove):
                r = state.active_connections.pop()
                r.close()
            logger.info(f"Released connections. Remaining: {len(state.active_connections)}")

    # 3. Memory Fill (Eviction Storm)
    if config.fill_memory_mb is not None:
        if config.fill_memory_mb > 0 and not state.memory_fill_active:
            state.memory_fill_active = True
            state.memory_fill_thread = threading.Thread(target=fill_memory_task, args=(config.fill_memory_mb,))
            state.memory_fill_thread.start()
        elif config.fill_memory_mb == 0 and state.memory_fill_active:
            state.memory_fill_active = False
            if state.memory_fill_thread:
                state.memory_fill_thread.join()
            # Optional: Cleanup keys? For now, leave them to simulate full cache.

    # 4. CPU Burn (Hot Key simulation)
    if config.cpu_burn is not None:
        if config.cpu_burn and not state.cpu_burn_active:
            state.cpu_burn_active = True
            state.cpu_burn_thread = threading.Thread(target=cpu_burn_task)
            state.cpu_burn_thread.start()
        elif not config.cpu_burn and state.cpu_burn_active:
            state.cpu_burn_active = False
            if state.cpu_burn_thread:
                state.cpu_burn_thread.join()

    return {"status": "updated", "state": {
        "connections": len(state.active_connections),
        "memory_fill": state.memory_fill_active,
        "cpu_burn": state.cpu_burn_active
    }}

@app.post("/control/reset")
async def reset_chaos():
    """Reset all chaos."""
    # Close connections
    for r in state.active_connections:
        r.close()
    state.active_connections.clear()

    # Stop Threads
    state.memory_fill_active = False
    state.cpu_burn_active = False
    if state.memory_fill_thread: state.memory_fill_thread.join()
    if state.cpu_burn_thread: state.cpu_burn_thread.join()

    # Cleanup Chaos Keys
    r = get_redis_connection()
    if r:
        # Delete chaos keys
        keys = r.keys("chaos:memfill:*")
        if keys:
            r.delete(*keys)
            logger.info(f"Cleaned up {len(keys)} chaos keys")

    return {"status": "reset"}

@app.get("/health")
async def health():
    r = get_redis_connection()
    status = "up"
    try:
        if r: r.ping()
        else: status = "down"
    except:
        status = "down"
    finally:
        if r: r.close()
    return {"status": "healthy", "redis_connection": status}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
