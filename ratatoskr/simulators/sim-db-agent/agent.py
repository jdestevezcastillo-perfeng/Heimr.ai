import asyncio
import logging
import os
import time
import psycopg2
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import threading

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("sim-db-agent")

app = FastAPI(title="Heimr.ai DB Chaos Agent")

# DB Config
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "postgres")
DB_NAME = os.getenv("DB_NAME", "postgres")

class ChaosState:
    active_connections: List[any] = []
    locked_tables: List[any] = []
    io_burn_active: bool = False
    io_thread = None

state = ChaosState()

class ChaosConfig(BaseModel):
    connection_leak_count: Optional[int] = 0
    lock_table: Optional[str] = None
    io_burn: Optional[bool] = False

def get_db_connection():
    try:
        return psycopg2.connect(
            host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASS, dbname=DB_NAME
        )
    except Exception as e:
        logger.error(f"Failed to connect to DB: {e}")
        return None

def burn_io_task():
    """Writes junk data to disk to saturate I/O."""
    filename = "/tmp/io_burn.dat"
    logger.info("Starting I/O burn...")
    try:
        with open(filename, "wb") as f:
            while state.io_burn_active:
                f.write(os.urandom(1024 * 1024)) # 1MB chunks
                f.flush()
                os.fsync(f.fileno())
                time.sleep(0.01) # Slight throttle to prevent total system freeze
    except Exception as e:
        logger.error(f"I/O burn failed: {e}")
    finally:
        if os.path.exists(filename):
            os.remove(filename)
        logger.info("Stopped I/O burn.")

@app.post("/control/chaos")
async def set_chaos(config: ChaosConfig):
    """Inject DB faults."""
    
    # 1. Connection Leak
    if config.connection_leak_count is not None:
        current_count = len(state.active_connections)
        target_count = config.connection_leak_count
        
        if target_count > current_count:
            # Add connections
            for _ in range(target_count - current_count):
                conn = get_db_connection()
                if conn:
                    state.active_connections.append(conn)
            logger.info(f"Leaked connections: {len(state.active_connections)}")
        elif target_count < current_count:
            # Remove connections
            to_remove = current_count - target_count
            for _ in range(to_remove):
                conn = state.active_connections.pop()
                conn.close()
            logger.info(f"Released connections. Remaining: {len(state.active_connections)}")

    # 2. Table Locking
    if config.lock_table:
        # Check if already locked
        if not any(t['table'] == config.lock_table for t in state.locked_tables):
            conn = get_db_connection()
            if conn:
                try:
                    cur = conn.cursor()
                    # LOCK TABLE IN ACCESS EXCLUSIVE MODE - Blocks reads and writes!
                    cur.execute(f"BEGIN; LOCK TABLE {config.lock_table} IN ACCESS EXCLUSIVE MODE;")
                    # Do NOT commit. Hold the transaction open.
                    state.locked_tables.append({'table': config.lock_table, 'conn': conn})
                    logger.info(f"Locked table: {config.lock_table}")
                except Exception as e:
                    logger.error(f"Failed to lock table {config.lock_table}: {e}")
                    conn.close()

    # 3. I/O Burn
    if config.io_burn is not None:
        if config.io_burn and not state.io_burn_active:
            state.io_burn_active = True
            state.io_thread = threading.Thread(target=burn_io_task)
            state.io_thread.start()
        elif not config.io_burn and state.io_burn_active:
            state.io_burn_active = False
            if state.io_thread:
                state.io_thread.join()

    return {"status": "updated", "state": {
        "connections": len(state.active_connections),
        "locked_tables": [t['table'] for t in state.locked_tables],
        "io_burn": state.io_burn_active
    }}

@app.post("/control/reset")
async def reset_chaos():
    """Reset all chaos."""
    # Close connections
    for conn in state.active_connections:
        conn.close()
    state.active_connections.clear()

    # Release locks
    for item in state.locked_tables:
        item['conn'].rollback() # Rollback releases locks
        item['conn'].close()
    state.locked_tables.clear()

    # Stop I/O burn
    state.io_burn_active = False
    if state.io_thread:
        state.io_thread.join()

    return {"status": "reset"}

@app.get("/health")
async def health():
    # Check DB connectivity
    conn = get_db_connection()
    db_status = "up" if conn else "down"
    if conn: conn.close()
    return {"status": "healthy", "db_connection": db_status}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
