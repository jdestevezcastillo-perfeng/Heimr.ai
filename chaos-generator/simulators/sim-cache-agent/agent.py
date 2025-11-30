import asyncio
import logging
import os
import redis
import threading
import time
import random
import json
import sys
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, List

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
            "service": "sim-cache-agent"
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
logger = logging.getLogger("sim-cache-agent")

# Configure OpenTelemetry
resource = Resource.create({
    "service.name": "sim-cache-agent",
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

app = FastAPI(title="Heimr.ai Cache Chaos Agent")

from prometheus_client import make_asgi_app, Gauge, Counter, Histogram
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# ========================================
# COMPREHENSIVE REDIS METRICS
# ========================================

# Command Metrics
REDIS_COMMANDS_TOTAL = Counter('redis_commands_total', 'Total commands processed', ['command', 'status'])
REDIS_COMMAND_DURATION = Histogram('redis_command_duration_seconds', 'Command latency', ['command'])

# Cache Hit/Miss Metrics
REDIS_HITS_TOTAL = Counter('redis_keyspace_hits_total', 'Cache hits')
REDIS_MISSES_TOTAL = Counter('redis_keyspace_misses_total', 'Cache misses')
REDIS_HIT_RATE = Gauge('redis_hit_rate', 'Cache hit rate percentage')

# Memory Metrics
REDIS_MEMORY_USED = Gauge('redis_memory_used_bytes', 'Memory used by Redis')
REDIS_MEMORY_RSS = Gauge('redis_memory_rss_bytes', 'Resident set size')
REDIS_MEMORY_PEAK = Gauge('redis_memory_peak_bytes', 'Peak memory used')
REDIS_MEMORY_FRAGMENTATION_RATIO = Gauge('redis_memory_fragmentation_ratio', 'Memory fragmentation ratio')

# Key Metrics
REDIS_KEYS_TOTAL = Gauge('redis_db_keys', 'Total keys in database', ['db'])
REDIS_EXPIRES_TOTAL = Gauge('redis_db_keys_expiring', 'Keys with TTL set', ['db'])
REDIS_AVG_TTL = Gauge('redis_db_avg_ttl_seconds', 'Average TTL', ['db'])

# Expiration/Eviction Metrics
REDIS_EXPIRED_KEYS = Counter('redis_expired_keys_total', 'Total expired keys')
REDIS_EVICTED_KEYS = Counter('redis_evicted_keys_total', 'Total evicted keys')

# Connection Metrics
REDIS_CONNECTED_CLIENTS = Gauge('redis_connected_clients', 'Number of connected clients')
REDIS_BLOCKED_CLIENTS = Gauge('redis_blocked_clients', 'Clients blocked on blocking calls')
REDIS_CLIENT_LONGEST_OUTPUT_LIST = Gauge('redis_client_longest_output_list', 'Longest output list')

# Network Metrics
REDIS_NET_INPUT_BYTES = Counter('redis_net_input_bytes_total', 'Total network input bytes')
REDIS_NET_OUTPUT_BYTES = Counter('redis_net_output_bytes_total', 'Total network output bytes')

# Persistence Metrics
REDIS_RDB_CHANGES_SINCE_LAST_SAVE = Gauge('redis_rdb_changes_since_last_save', 'Changes since last save')
REDIS_RDB_LAST_SAVE_TIME = Gauge('redis_rdb_last_save_timestamp_seconds', 'Last save timestamp')
REDIS_RDB_LAST_BGSAVE_STATUS = Gauge('redis_rdb_last_bgsave_status', '1 if OK, 0 if failed')

# Replication Metrics (if slave)
REDIS_MASTER_LINK_STATUS = Gauge('redis_master_link_up', '1 if link is up, 0 if down')
REDIS_MASTER_LAST_IO_SECONDS = Gauge('redis_master_last_io_seconds_ago', 'Seconds since last IO')

# Ops Metrics
REDIS_OPS_PER_SEC = Gauge('redis_instantaneous_ops_per_sec', 'Ops per second')

# Chaos Injection Metrics (existing)
CACHE_LEAKED_CONNECTIONS = Gauge('cache_leaked_connections', 'Number of leaked connections')

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
    # Simulated cache state
    total_keys = 10000
    memory_used_mb = 100

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
        logger.error(f"Failed to connect to Redis: {e}", exc_info=True)
        return None

def fill_memory_task(target_mb):
    """Fills Redis memory with junk data."""
    logger.info(f"Starting memory fill target={target_mb}MB...")
    r = get_redis_connection()
    if not r: return

    chunk_size = 1024 * 1024
    key_prefix = "chaos:memfill:"
    count = 0
    
    try:
        while state.memory_fill_active and count < target_mb:
            r.set(f"{key_prefix}{count}", "X" * chunk_size)
            count += 1
            state.memory_used_mb = state.memory_used_mb + 1
            time.sleep(0.1)
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
            r.keys("*")
            time.sleep(0.01)
    except Exception as e:
        logger.error(f"CPU burn failed: {e}")
    finally:
        logger.info("Stopped CPU burn.")

async def simulate_redis_activity():
    """Background task that generates realistic Redis metrics"""
    logger.info("Starting Redis activity simulation...")
    commands = ['GET', 'SET', 'DEL', 'INCR', 'LPUSH', 'SADD', 'ZADD', 'HSET']
    
    while True:
        # Simulate command activity
        command = random.choices(commands, weights=[50, 30, 5, 5, 3, 3, 2, 2])[0]
        
        # Command duration with realistic distribution
        base_duration = {'GET': 0.0001, 'SET': 0.0002, 'DEL': 0.0001, 
                        'INCR': 0.0001, 'LPUSH': 0.0002, 'SADD': 0.0002,
                        'ZADD': 0.0003, 'HSET': 0.0002}[command]
        duration = random.expovariate(1.0 / base_duration)
        
        REDIS_COMMAND_DURATION.labels(command=command).observe(duration)
        REDIS_COMMANDS_TOTAL.labels(command=command, status='success').inc()
        
        # Cache hit/miss (85% hit rate baseline)
        if command in ['GET', 'INCR']:
            if random.random() < 0.85:
                REDIS_HITS_TOTAL.inc()
            else:
                REDIS_MISSES_TOTAL.inc()
        
        # Update hit rate
        total_hits = REDIS_HITS_TOTAL._value._value
        total_misses = REDIS_MISSES_TOTAL._value._value
        total_lookups = total_hits + total_misses
        if total_lookups > 0:
            REDIS_HIT_RATE.set(total_hits / total_lookups * 100)
        
        # Memory metrics (fluctuate)
        memory_used = (state.memory_used_mb * 1024 * 1024) + random.randint(-1024, 1024)
        REDIS_MEMORY_USED.set(memory_used)
        REDIS_MEMORY_RSS.set(int(memory_used * 1.1))  # RSS slightly higher
        REDIS_MEMORY_PEAK.set(int(memory_used * 1.2))
        REDIS_MEMORY_FRAGMENTATION_RATIO.set(random.uniform(1.0, 1.5))
        
        # Key metrics
        keys = max(1, state.total_keys + random.randint(-100, 100))
        expires = int(keys * random.uniform(0.3, 0.5))
        REDIS_KEYS_TOTAL.labels(db=str(REDIS_DB)).set(keys)
        REDIS_EXPIRES_TOTAL.labels(db=str(REDIS_DB)).set(expires)
        REDIS_AVG_TTL.labels(db=str(REDIS_DB)).set(random.uniform(300, 3600))
        
        # Expirations/Evictions
        if random.random() < 0.05:
            REDIS_EXPIRED_KEYS.inc(random.randint(1, 10))
        
        # Evictions happen when memory is full
        if state.memory_fill_active and random.random() < 0.1:
            REDIS_EVICTED_KEYS.inc(random.randint(1, 5))
        
        # Connection metrics
        connected = len(state.active_connections) + random.randint(10, 20)
        blocked = random.randint(0, 3) if state.cpu_burn_active else 0
        REDIS_CONNECTED_CLIENTS.set(connected)
        REDIS_BLOCKED_CLIENTS.set(blocked)
        REDIS_CLIENT_LONGEST_OUTPUT_LIST.set(random.randint(0, 100))
        
        # Network metrics
        REDIS_NET_INPUT_BYTES.inc(random.randint(1000, 10000))
        REDIS_NET_OUTPUT_BYTES.inc(random.randint(2000, 20000))
        
        # Persistence
        REDIS_RDB_CHANGES_SINCE_LAST_SAVE.set(random.randint(100, 1000))
        REDIS_RDB_LAST_SAVE_TIME.set(time.time() - random.randint(60, 600))
        REDIS_RDB_LAST_BGSAVE_STATUS.set(1)  # OK
        
        # Replication (assume connected)
        REDIS_MASTER_LINK_STATUS.set(1)
        REDIS_MASTER_LAST_IO_SECONDS.set(random.randint(0, 5))
        
        # Ops per second
        REDIS_OPS_PER_SEC.set(random.randint(1000, 5000))
        
        await asyncio.sleep(0.1)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(simulate_redis_activity())

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Tie metrics to actual HTTP traffic"""
    if request.url.path not in ["/metrics", "/health"]:
        # Spike activity on requests
        for _ in range(5):
            command = random.choice(['GET', 'SET'])
            duration = random.expovariate(10000.0)
            REDIS_COMMAND_DURATION.labels(command=command).observe(duration)
    
    response = await call_next(request)
    return response

@app.post("/control/chaos")
async def set_chaos(config: ChaosConfig):
    """Inject Cache faults."""
    
    # Cache Stampede (Flush All)
    if config.flush_all:
        r = get_redis_connection()
        if r:
            r.flushall()
            state.total_keys = 0
            logger.info("Executed FLUSHALL")
        else:
            raise HTTPException(status_code=500, detail="Could not connect to Redis")

    # Connection Leak
    if config.connection_leak_count is not None:
        current_count = len(state.active_connections)
        target_count = config.connection_leak_count
        
        if target_count > current_count:
            for _ in range(target_count - current_count):
                r = get_redis_connection()
                if r:
                    r.ping()
                    state.active_connections.append(r)
            logger.info(f"Leaked connections: {len(state.active_connections)}")
        elif target_count < current_count:
            to_remove = current_count - target_count
            for _ in range(to_remove):
                r = state.active_connections.pop()
                r.close()
            logger.info(f"Released connections. Remaining: {len(state.active_connections)}")

    # Memory Fill (Eviction Storm)
    if config.fill_memory_mb is not None:
        if config.fill_memory_mb > 0 and not state.memory_fill_active:
            state.memory_fill_active = True
            state.memory_fill_thread = threading.Thread(target=fill_memory_task, args=(config.fill_memory_mb,))
            state.memory_fill_thread.start()
        elif config.fill_memory_mb == 0 and state.memory_fill_active:
            state.memory_fill_active = False
            if state.memory_fill_thread:
                state.memory_fill_thread.join()

    # CPU Burn (Hot Key simulation)
    if config.cpu_burn is not None:
        if config.cpu_burn and not state.cpu_burn_active:
            state.cpu_burn_active = True
            state.cpu_burn_thread = threading.Thread(target=cpu_burn_task)
            state.cpu_burn_thread.start()
        elif not config.cpu_burn and state.cpu_burn_active:
            state.cpu_burn_active = False
            if state.cpu_burn_thread:
                state.cpu_burn_thread.join()

    CACHE_LEAKED_CONNECTIONS.set(len(state.active_connections))

    return {"status": "updated", "state": {
        "connections": len(state.active_connections),
        "memory_fill": state.memory_fill_active,
        "cpu_burn": state.cpu_burn_active
    }}

@app.post("/control/reset")
async def reset_chaos():
    """Reset all chaos."""
    for r in state.active_connections:
        r.close()
    state.active_connections.clear()

    state.memory_fill_active = False
    state.cpu_burn_active = False
    if state.memory_fill_thread: state.memory_fill_thread.join()
    if state.cpu_burn_thread: state.cpu_burn_thread.join()

    # Cleanup Chaos Keys
    r = get_redis_connection()
    if r:
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
