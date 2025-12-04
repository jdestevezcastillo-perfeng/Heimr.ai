# Copyright (c) 2025 Juan Estevez Castillo
# Licensed under AGPL v3. Commercial licenses available.
# See LICENSE or https://www.gnu.org/licenses/agpl-3.0.html
"""
Heimr Test Application - FastAPI with OpenTelemetry instrumentation
For testing Heimr with real observability data
"""
import os
import time
import random
import logging
import asyncio
import psycopg2
from psycopg2 import pool
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

# OpenTelemetry imports
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor

# Configure logging (JSON format for Loki)
logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","message":"%(message)s"}'
)
logger = logging.getLogger("test-app")

# Prometheus metrics
REQUEST_COUNT = Counter(
    'http_requests_total', 
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)
REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

# Chaos injection settings (controlled via environment)
CHAOS_SLOW_ENABLED = os.getenv("CHAOS_SLOW_ENABLED", "false").lower() == "true"
CHAOS_SLOW_DELAY_MS = int(os.getenv("CHAOS_SLOW_DELAY_MS", "2000"))
CHAOS_ERROR_ENABLED = os.getenv("CHAOS_ERROR_ENABLED", "false").lower() == "true"
CHAOS_ERROR_RATE = float(os.getenv("CHAOS_ERROR_RATE", "0.3"))
CHAOS_MEMORY_LEAK = os.getenv("CHAOS_MEMORY_LEAK", "false").lower() == "true"

# Memory leak list (for chaos testing)
memory_leak_list = []

# Database connection
DB_HOST = os.getenv("DB_HOST", "postgres")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "testdb")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")

# Connection pool
db_pool = None


def get_db_connection():
    """Get a database connection from the pool."""
    global db_pool
    if db_pool is None:
        db_pool = psycopg2.pool.SimpleConnectionPool(
            1, 20,
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
    return db_pool.getconn()


def return_db_connection(conn):
    """Return a connection to the pool."""
    global db_pool
    if db_pool:
        db_pool.putconn(conn)


# Models
class User(BaseModel):
    id: Optional[int] = None
    username: str
    email: str
    created_at: Optional[datetime] = None


class AuditLog(BaseModel):
    id: int
    user_id: int
    action: str
    resource: str
    response_code: int
    duration_ms: int
    created_at: datetime


class HealthResponse(BaseModel):
    status: str
    database: str
    chaos_slow: bool
    chaos_error: bool
    chaos_memory_leak: bool


# OpenTelemetry setup
def setup_telemetry():
    """Configure OpenTelemetry tracing."""
    tempo_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "tempo:4317")
    
    provider = TracerProvider()
    processor = BatchSpanProcessor(
        OTLPSpanExporter(
            endpoint=tempo_endpoint,
            insecure=True
        )
    )
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)
    
    # Instrument psycopg2
    Psycopg2Instrumentor().instrument()
    
    logger.info(f"OpenTelemetry configured with endpoint: {tempo_endpoint}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    setup_telemetry()
    logger.info("Test application starting up")
    
    # Wait for database
    for i in range(30):
        try:
            conn = get_db_connection()
            return_db_connection(conn)
            logger.info("Database connection established")
            break
        except Exception as e:
            logger.warning(f"Waiting for database... ({i+1}/30)")
            await asyncio.sleep(1)
    
    yield
    
    # Shutdown
    logger.info("Test application shutting down")
    if db_pool:
        db_pool.closeall()


# Create FastAPI app
app = FastAPI(
    title="Heimr Test Application",
    description="Test application for Heimr observability testing",
    version="1.0.0",
    lifespan=lifespan
)

# Instrument FastAPI
FastAPIInstrumentor.instrument_app(app)


@app.middleware("http")
async def metrics_middleware(request, call_next):
    """Middleware to record metrics and apply chaos."""
    start_time = time.time()
    
    # Chaos: Random slow response
    if CHAOS_SLOW_ENABLED and random.random() < 0.3:
        await asyncio.sleep(CHAOS_SLOW_DELAY_MS / 1000.0)
        logger.warning(f"CHAOS: Injected slow response ({CHAOS_SLOW_DELAY_MS}ms)")
    
    # Chaos: Random error
    if CHAOS_ERROR_ENABLED and random.random() < CHAOS_ERROR_RATE:
        logger.error("CHAOS: Injected random error")
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            status="500"
        ).inc()
        return Response(
            content='{"error": "Chaos injection: Random error"}',
            status_code=500,
            media_type="application/json"
        )
    
    # Chaos: Memory leak
    if CHAOS_MEMORY_LEAK:
        # Add 1KB of data per request (accumulates over time)
        memory_leak_list.append("X" * 1024)
        if len(memory_leak_list) % 1000 == 0:
            logger.warning(f"CHAOS: Memory leak size: {len(memory_leak_list)} KB")
    
    response = await call_next(request)
    
    duration = time.time() - start_time
    
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status=str(response.status_code)
    ).inc()
    
    REQUEST_DURATION.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(duration)
    
    return response


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint."""
    db_status = "unknown"
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        return_db_connection(conn)
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
        logger.error(f"Database health check failed: {e}")
    
    return HealthResponse(
        status="ok",
        database=db_status,
        chaos_slow=CHAOS_SLOW_ENABLED,
        chaos_error=CHAOS_ERROR_ENABLED,
        chaos_memory_leak=CHAOS_MEMORY_LEAK
    )


@app.get("/metrics", tags=["Metrics"])
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


@app.get("/api/users", response_model=List[User], tags=["Users"])
async def list_users(limit: int = Query(default=10, le=100)):
    """List users (indexed table - fast)."""
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("list_users") as span:
        span.set_attribute("limit", limit)
        
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute(
                "SELECT id, username, email, created_at FROM users LIMIT %s",
                (limit,)
            )
            rows = cur.fetchall()
            cur.close()
            return_db_connection(conn)
            
            users = [
                User(id=r[0], username=r[1], email=r[2], created_at=r[3])
                for r in rows
            ]
            logger.info(f"Listed {len(users)} users")
            return users
        except Exception as e:
            logger.error(f"Failed to list users: {e}")
            raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/users", response_model=User, tags=["Users"])
async def create_user(user: User):
    """Create a new user."""
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("create_user") as span:
        span.set_attribute("username", user.username)
        
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO users (username, email) VALUES (%s, %s) RETURNING id, created_at",
                (user.username, user.email)
            )
            result = cur.fetchone()
            conn.commit()
            cur.close()
            return_db_connection(conn)
            
            user.id = result[0]
            user.created_at = result[1]
            logger.info(f"Created user: {user.username}")
            return user
        except Exception as e:
            logger.error(f"Failed to create user: {e}")
            raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/audit-logs", response_model=List[AuditLog], tags=["Audit"])
async def list_audit_logs(
    user_id: Optional[int] = None,
    action: Optional[str] = None,
    limit: int = Query(default=100, le=1000)
):
    """
    Query audit logs (UNINDEXED table - SLOW!).
    This endpoint is designed to be slow for testing purposes.
    The audit_logs table has 1M rows with NO indexes.
    """
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("list_audit_logs") as span:
        span.set_attribute("limit", limit)
        span.set_attribute("user_id", user_id or "all")
        span.set_attribute("action", action or "all")
        
        start = time.time()
        
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            # Build query (will be SLOW due to no indexes!)
            query = """
                SELECT id, user_id, action, resource, response_code, duration_ms, created_at 
                FROM audit_logs 
                WHERE 1=1
            """
            params = []
            
            if user_id:
                query += " AND user_id = %s"
                params.append(user_id)
            if action:
                query += " AND action = %s"
                params.append(action)
            
            query += " ORDER BY created_at DESC LIMIT %s"
            params.append(limit)
            
            cur.execute(query, params)
            rows = cur.fetchall()
            cur.close()
            return_db_connection(conn)
            
            duration = time.time() - start
            span.set_attribute("query_duration_ms", int(duration * 1000))
            
            logs = [
                AuditLog(
                    id=r[0], user_id=r[1], action=r[2], resource=r[3],
                    response_code=r[4], duration_ms=r[5], created_at=r[6]
                )
                for r in rows
            ]
            
            logger.info(f"Queried audit_logs: {len(logs)} rows in {duration:.2f}s (SLOW - no index)")
            if duration > 1.0:
                logger.warning(f"SLOW QUERY: audit_logs took {duration:.2f}s")
            
            return logs
        except Exception as e:
            logger.error(f"Failed to query audit logs: {e}")
            raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/audit-logs/count", tags=["Audit"])
async def count_audit_logs():
    """
    Count audit logs (UNINDEXED table - can be slow).
    """
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("count_audit_logs"):
        start = time.time()
        
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM audit_logs")
            count = cur.fetchone()[0]
            cur.close()
            return_db_connection(conn)
            
            duration = time.time() - start
            logger.info(f"Counted {count} audit logs in {duration:.2f}s")
            
            return {"count": count, "duration_ms": int(duration * 1000)}
        except Exception as e:
            logger.error(f"Failed to count audit logs: {e}")
            raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/slow", tags=["Chaos"])
async def slow_endpoint(delay_ms: int = Query(default=1000, le=10000)):
    """
    Configurable slow endpoint for testing.
    Simulates slow API response.
    """
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("slow_endpoint") as span:
        span.set_attribute("delay_ms", delay_ms)
        
        logger.info(f"Slow endpoint: sleeping for {delay_ms}ms")
        await asyncio.sleep(delay_ms / 1000.0)
        
        return {"message": "Slow response", "delay_ms": delay_ms}


@app.get("/api/error", tags=["Chaos"])
async def error_endpoint(status_code: int = Query(default=500, ge=400, le=599)):
    """
    Configurable error endpoint for testing.
    Always returns an error with the specified status code.
    """
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("error_endpoint") as span:
        span.set_attribute("error_code", status_code)
        
        logger.error(f"Error endpoint: returning {status_code}")
        raise HTTPException(status_code=status_code, detail=f"Intentional error: {status_code}")


@app.post("/api/chaos/enable-slow", tags=["Chaos"])
async def enable_slow_chaos(delay_ms: int = Query(default=2000)):
    """Enable slow chaos injection."""
    global CHAOS_SLOW_ENABLED, CHAOS_SLOW_DELAY_MS
    CHAOS_SLOW_ENABLED = True
    CHAOS_SLOW_DELAY_MS = delay_ms
    logger.warning(f"CHAOS ENABLED: Slow responses ({delay_ms}ms)")
    return {"chaos": "slow", "enabled": True, "delay_ms": delay_ms}


@app.post("/api/chaos/enable-error", tags=["Chaos"])
async def enable_error_chaos(rate: float = Query(default=0.3, ge=0, le=1)):
    """Enable error chaos injection."""
    global CHAOS_ERROR_ENABLED, CHAOS_ERROR_RATE
    CHAOS_ERROR_ENABLED = True
    CHAOS_ERROR_RATE = rate
    logger.warning(f"CHAOS ENABLED: Random errors ({rate*100}% rate)")
    return {"chaos": "error", "enabled": True, "rate": rate}


@app.post("/api/chaos/enable-memory-leak", tags=["Chaos"])
async def enable_memory_leak():
    """Enable memory leak chaos injection."""
    global CHAOS_MEMORY_LEAK
    CHAOS_MEMORY_LEAK = True
    logger.warning("CHAOS ENABLED: Memory leak")
    return {"chaos": "memory_leak", "enabled": True}


@app.post("/api/chaos/disable-all", tags=["Chaos"])
async def disable_all_chaos():
    """Disable all chaos injection."""
    global CHAOS_SLOW_ENABLED, CHAOS_ERROR_ENABLED, CHAOS_MEMORY_LEAK, memory_leak_list
    CHAOS_SLOW_ENABLED = False
    CHAOS_ERROR_ENABLED = False
    CHAOS_MEMORY_LEAK = False
    memory_leak_list = []  # Clear leaked memory
    logger.info("CHAOS DISABLED: All chaos injection disabled")
    return {"chaos": "all", "enabled": False}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
