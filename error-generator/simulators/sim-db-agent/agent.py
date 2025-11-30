import asyncio
import logging
import os
import time
import psycopg2
import random
import json
import sys
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, List
import threading

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
            "service": "sim-db-agent"
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
logger = logging.getLogger("sim-db-agent")

# Configure OpenTelemetry
resource = Resource.create({
    "service.name": "sim-db-agent",
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

app = FastAPI(title="Heimr.ai DB Chaos Agent")

from prometheus_client import make_asgi_app, Gauge, Counter, Histogram
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# ========================================
# COMPREHENSIVE POSTGRESQL METRICS
# ========================================

# Connection Metrics
DB_CONNECTIONS_ACTIVE = Gauge('pg_connections_active', 'Active connections', ['db', 'state'])
DB_CONNECTIONS_MAX = Gauge('pg_connections_max', 'Max connections', ['db'])
DB_CONNECTIONS_IDLE = Gauge('pg_connections_idle', 'Idle connections', ['db'])
DB_CONNECTIONS_WAITING = Gauge('pg_connections_waiting', 'Connections waiting', ['db'])

# Transaction Metrics
DB_TRANSACTIONS_TOTAL = Counter('pg_transactions_total', 'Total transactions', ['db', 'status'])
DB_TRANSACTION_DURATION = Histogram('pg_transaction_duration_seconds', 'Transaction duration', ['db'])

# Query Metrics  
DB_QUERY_DURATION = Histogram('pg_query_duration_seconds', 'Query execution time', ['query_type', 'db'])
DB_QUERIES_TOTAL = Counter('pg_queries_total', 'Total queries', ['query_type', 'db'])
DB_SLOW_QUERIES = Counter('pg_slow_queries_total', 'Queries exceeding threshold', ['db'])

# Lock Metrics
DB_LOCKS_TOTAL = Gauge('pg_locks_total', 'Total locks', ['db', 'mode'])
DB_DEADLOCKS_TOTAL = Counter('pg_deadlocks_total', 'Total deadlocks', ['db'])
DB_LOCK_WAIT_DURATION = Histogram('pg_lock_wait_duration_seconds', 'Lock wait time', ['db'])

# Cache Metrics
DB_CACHE_HIT_RATIO = Gauge('pg_cache_hit_ratio', 'Buffer cache hit ratio', ['db'])
DB_BLOCKS_HIT = Counter('pg_blocks_hit_total', 'Blocks read from cache', ['db'])
DB_BLOCKS_READ = Counter('pg_blocks_read_total', 'Blocks read from disk', ['db'])

# Row Operations
DB_ROWS_FETCHED = Counter('pg_rows_fetched_total', 'Rows fetched', ['db', 'table'])
DB_ROWS_INSERTED = Counter('pg_rows_inserted_total', 'Rows inserted', ['db', 'table'])
DB_ROWS_UPDATED = Counter('pg_rows_updated_total', 'Rows updated', ['db', 'table'])
DB_ROWS_DELETED = Counter('pg_rows_deleted_total', 'Rows deleted', ['db', 'table'])

# Table & Index Metrics
DB_TABLE_SIZE = Gauge('pg_table_size_bytes', 'Table size', ['db', 'table'])
DB_INDEX_SIZE = Gauge('pg_index_size_bytes', 'Index size', ['db', 'index'])
DB_INDEX_SCANS = Counter('pg_index_scans_total', 'Index scans', ['db', 'index'])
DB_SEQ_SCANS = Counter('pg_sequential_scans_total', 'Sequential scans', ['db', 'table'])

# Replication Metrics
DB_REPLICATION_LAG_BYTES = Gauge('pg_replication_lag_bytes', 'Replication lag in bytes', ['db'])
DB_REPLICATION_LAG_SECONDS = Gauge('pg_replication_lag_seconds', 'Replication lag in seconds', ['db'])

# Checkpointing & WAL
DB_CHECKPOINTS_TIMED = Counter('pg_checkpoints_timed_total', 'Timed checkpoints', ['db'])
DB_CHECKPOINTS_REQ = Counter('pg_checkpoints_requested_total', 'Requested checkpoints', ['db'])
DB_WAL_RECORDS = Counter('pg_wal_records_total', 'WAL records written', ['db'])
DB_WAL_BYTES = Counter('pg_wal_bytes_total', 'WAL bytes written', ['db'])

# Chaos Injection Metrics (existing)
DB_LEAKED_CONNECTIONS = Gauge('db_active_connections', 'Number of leaked DB connections', ['db_host'])
DB_LOCKED_TABLES = Gauge('db_locked_tables', 'Number of tables currently locked', ['db_host'])

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
    # Simulated DB activity state
    total_connections = 10
    slow_query_threshold_ms = 1000

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
        logger.error(f"Failed to connect to DB: {e}", exc_info=True)
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
                time.sleep(0.01)
    except Exception as e:
        logger.error(f"I/O burn failed: {e}")
    finally:
        if os.path.exists(filename):
            os.remove(filename)
        logger.info("Stopped I/O burn.")

async def simulate_db_activity():
    """Background task that generates realistic PostgreSQL metrics"""
    logger.info("Starting DB activity simulation...")
    tables = ['users', 'orders', 'products', 'sessions']
    indexes = ['users_email_idx', 'orders_user_id_idx', 'products_sku_idx']
    
    while True:
        # Simulate query activity
        query_type = random.choices(
            ['select', 'insert', 'update', 'delete'],
            weights=[70, 15, 10, 5]
        )[0]
        table = random.choice(tables)
        
        # Query duration with realistic distribution
        base_duration = {'select': 0.005, 'insert': 0.010, 'update': 0.015, 'delete': 0.020}[query_type]
        duration = random.expovariate(1.0 / base_duration)
        
        DB_QUERY_DURATION.labels(query_type=query_type, db=DB_NAME).observe(duration)
        DB_QUERIES_TOTAL.labels(query_type=query_type, db=DB_NAME).inc()
        
        # Slow query detection
        if duration > (state.slow_query_threshold_ms / 1000.0):
            DB_SLOW_QUERIES.labels(db=DB_NAME).inc()
        
        # Row operations
        rows = random.randint(1, 100)
        if query_type == 'select':
            DB_ROWS_FETCHED.labels(db=DB_NAME, table=table).inc(rows)
        elif query_type == 'insert':
            DB_ROWS_INSERTED.labels(db=DB_NAME, table=table).inc(rows)
        elif query_type == 'update':
            DB_ROWS_UPDATED.labels(db=DB_NAME, table=table).inc(rows)
        elif query_type == 'delete':
            DB_ROWS_DELETED.labels(db=DB_NAME, table=table).inc(rows)
        
        # Index vs sequential scans (70% index, 30% seq)
        if random.random() < 0.7:
            DB_INDEX_SCANS.labels(db=DB_NAME, index=random.choice(indexes)).inc()
        else:
            DB_SEQ_SCANS.labels(db=DB_NAME, table=table).inc()
        
        # Cache metrics (85% hit ratio baseline)
        blocks_accessed = random.randint(10, 1000)
        if random.random() < 0.85:
            DB_BLOCKS_HIT.labels(db=DB_NAME).inc(blocks_accessed)
        else:
            DB_BLOCKS_READ.labels(db=DB_NAME).inc(blocks_accessed)
        
        # Update cache hit ratio
        total_hits = DB_BLOCKS_HIT.labels(db=DB_NAME)._value._value
        total_reads = DB_BLOCKS_READ.labels(db=DB_NAME)._value._value
        total_access = total_hits + total_reads
        if total_access > 0:
            DB_CACHE_HIT_RATIO.labels(db=DB_NAME).set(total_hits / total_access)
        
        # Transactions (commit/rollback 98%/2%)
        if random.random() < 0.98:
            DB_TRANSACTIONS_TOTAL.labels(db=DB_NAME, status='commit').inc()
        else:
            DB_TRANSACTIONS_TOTAL.labels(db=DB_NAME, status='rollback').inc()
        
        DB_TRANSACTION_DURATION.labels(db=DB_NAME).observe(random.expovariate(20.0))
        
        # Connections (fluctuate around 10)
        active = max(1, state.total_connections + random.randint(-2, 2))
        idle = random.randint(0, 5)
        waiting = 0 if len(state.locked_tables) == 0 else random.randint(1, 5)
        
        DB_CONNECTIONS_ACTIVE.labels(db=DB_NAME, state='active').set(active)
        DB_CONNECTIONS_ACTIVE.labels(db=DB_NAME, state='idle').set(idle)
        DB_CONNECTIONS_IDLE.labels(db=DB_NAME).set(idle)
        DB_CONNECTIONS_WAITING.labels(db=DB_NAME).set(waiting)
        DB_CONNECTIONS_MAX.labels(db=DB_NAME).set(100)
        
        # Locks (increase if tables are locked)
        lock_count = len(state.locked_tables) * 10 + random.randint(1, 5)
        DB_LOCKS_TOTAL.labels(db=DB_NAME, mode='AccessExclusiveLock').set(lock_count if len(state.locked_tables) > 0 else random.randint(0, 2))
        DB_LOCKS_TOTAL.labels(db=DB_NAME, mode='RowExclusiveLock').set(random.randint(2, 10))
        
        # Occasional deadlock
        if random.random() < 0.001:
            DB_DEADLOCKS_TOTAL.labels(db=DB_NAME).inc()
        
        # Table sizes (slowly growing)
        for table in tables:
            size = 1024 * 1024 * random.randint(100, 500)
            DB_TABLE_SIZE.labels(db=DB_NAME, table=table).set(size)
        
        # Index sizes
        for index in indexes:
            size = 1024 * 1024 * random.randint(10, 50)
            DB_INDEX_SIZE.labels(db=DB_NAME, index=index).set(size)
        
        # Replication lag (simulate 0-5 seconds)
        lag_seconds = random.uniform(0, 5) if random.random() < 0.3 else 0
        DB_REPLICATION_LAG_SECONDS.labels(db=DB_NAME).set(lag_seconds)
        DB_REPLICATION_LAG_BYTES.labels(db=DB_NAME).set(int(lag_seconds * 1024 * 1024))
        
        # WAL writes
        if random.random() < 0.1:
            DB_WAL_RECORDS.labels(db=DB_NAME).inc(random.randint(100, 1000))
            DB_WAL_BYTES.labels(db=DB_NAME).inc(random.randint(1024, 10240))
        
        # Checkpoints
        if random.random() < 0.01:
            if random.random() < 0.7:
                DB_CHECKPOINTS_TIMED.labels(db=DB_NAME).inc()
            else:
                DB_CHECKPOINTS_REQ.labels(db=DB_NAME).inc()
        
        await asyncio.sleep(0.1)  # 10 queries/sec baseline

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(simulate_db_activity())

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Tie metrics to actual HTTP traffic"""
    # Spike activity on requests
    if request.url.path not in ["/metrics", "/health"]:
        # Triple query rate during actual traffic
        for _ in range(3):
            query_type = random.choice(['select', 'insert'])
            duration = random.expovariate(100.0)
            DB_QUERY_DURATION.labels(query_type=query_type, db=DB_NAME).observe(duration)
    
    response = await call_next(request)
    return response

@app.post("/control/chaos")
async def set_chaos(config: ChaosConfig):
    """Inject DB faults."""
    
    # Connection Leak
    if config.connection_leak_count is not None:
        current_count = len(state.active_connections)
        target_count = config.connection_leak_count
        
        if target_count > current_count:
            for _ in range(target_count - current_count):
                conn = get_db_connection()
                if conn:
                    state.active_connections.append(conn)
            logger.info(f"Leaked connections: {len(state.active_connections)}")
        elif target_count < current_count:
            to_remove = current_count - target_count
            for _ in range(to_remove):
                conn = state.active_connections.pop()
                conn.close()
            logger.info(f"Released connections. Remaining: {len(state.active_connections)}")

    # Table Locking
    if config.lock_table:
        if not any(t['table'] == config.lock_table for t in state.locked_tables):
            conn = get_db_connection()
            if conn:
                try:
                    cur = conn.cursor()
                    cur.execute(f"BEGIN; LOCK TABLE {config.lock_table} IN ACCESS EXCLUSIVE MODE;")
                    state.locked_tables.append({'table': config.lock_table, 'conn': conn})
                    logger.info(f"Locked table: {config.lock_table}")
                except Exception as e:
                    logger.error(f"Failed to lock table {config.lock_table}: {e}")
                    conn.close()

    # I/O Burn
    if config.io_burn is not None:
        if config.io_burn and not state.io_burn_active:
            state.io_burn_active = True
            state.io_thread = threading.Thread(target=burn_io_task)
            state.io_thread.start()
        elif not config.io_burn and state.io_burn_active:
            state.io_burn_active = False
            if state.io_thread:
                state.io_thread.join()

    DB_LEAKED_CONNECTIONS.labels(db_host=DB_HOST).set(len(state.active_connections))
    DB_LOCKED_TABLES.labels(db_host=DB_HOST).set(len(state.locked_tables))

    return {"status": "updated", "state": {
        "connections": len(state.active_connections),
        "locked_tables": [t['table'] for t in state.locked_tables],
        "io_burn": state.io_burn_active
    }}

@app.post("/control/reset")
async def reset_chaos():
    """Reset all chaos."""
    for conn in state.active_connections:
        conn.close()
    state.active_connections.clear()

    for item in state.locked_tables:
        item['conn'].rollback()
        item['conn'].close()
    state.locked_tables.clear()

    state.io_burn_active = False
    if state.io_thread:
        state.io_thread.join()

    return {"status": "reset"}

@app.get("/health")
async def health():
    conn = get_db_connection()
    db_status = "up" if conn else "down"
    if conn: conn.close()
    return {"status": "healthy", "db_connection": db_status}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
