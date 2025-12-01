import asyncio
import logging
import os
import random
import time
import httpx
import json
import sys
from fastapi import FastAPI, HTTPException, Response, Request
from pydantic import BaseModel
from typing import Optional

# OpenTelemetry imports
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

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
            "service": "sim-service-agent"
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
logger = logging.getLogger("sim-service")

# Configure OpenTelemetry
resource = Resource.create({
    "service.name": "sim-service-agent",
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
    # Use SimpleSpanProcessor for immediate export (synchronous) to avoid data loss in short windows
    span_processor = SimpleSpanProcessor(otlp_exporter)
    trace.get_tracer_provider().add_span_processor(span_processor)
    logger.info("OpenTelemetry tracing configured successfully")
except Exception as e:
    logger.warning(f"Failed to configure OpenTelemetry: {e}")

app = FastAPI(title="Heimr.ai Simulation Service")

# Instrument FastAPI with OpenTelemetry
FastAPIInstrumentor.instrument_app(app)

from prometheus_fastapi_instrumentator import Instrumentator
Instrumentator().instrument(app).expose(app)

# Global State for Chaos
class ChaosState:
    latency_ms: int = 0
    latency_jitter_ms: int = 0
    error_rate: float = 0.0
    memory_leak_bytes: int = 0
    cpu_burn_ms: int = 0
    leaked_memory = []

state = ChaosState()

class ChaosConfig(BaseModel):
    latency_ms: Optional[int] = 0
    latency_jitter_ms: Optional[int] = 0
    error_rate: Optional[float] = 0.0
    memory_leak_bytes: Optional[int] = 0
    cpu_burn_ms: Optional[int] = 0

@app.middleware("http")
async def chaos_middleware(request: Request, call_next):
    # 1. CPU Burn (Blocking)
    if state.cpu_burn_ms > 0:
        end_time = time.time() + (state.cpu_burn_ms / 1000.0)
        while time.time() < end_time:
            _ = 999999 * 999999

    # 2. Memory Leak
    if state.memory_leak_bytes > 0:
        state.leaked_memory.append(bytearray(state.memory_leak_bytes))

    # 3. Latency Injection
    if state.latency_ms > 0:
        delay = state.latency_ms
        if state.latency_jitter_ms > 0:
            delay += random.randint(0, state.latency_jitter_ms)
        await asyncio.sleep(delay / 1000.0)

    # 4. Error Injection
    if state.error_rate > 0 and random.random() < state.error_rate:
        logger.error(f"Chaos injection: returning 500 error (error_rate={state.error_rate})")
        return Response(content="Chaos Injection: 500 Internal Server Error", status_code=500)

    response = await call_next(request)
    return response

@app.post("/control/chaos")
async def set_chaos(config: ChaosConfig):
    """Configure chaos parameters dynamically."""
    if config.latency_ms is not None:
        state.latency_ms = config.latency_ms
    if config.latency_jitter_ms is not None:
        state.latency_jitter_ms = config.latency_jitter_ms
    if config.error_rate is not None:
        state.error_rate = config.error_rate
    if config.memory_leak_bytes is not None:
        state.memory_leak_bytes = config.memory_leak_bytes
    if config.cpu_burn_ms is not None:
        state.cpu_burn_ms = config.cpu_burn_ms
    
    logger.info(f"Chaos config updated: {state.__dict__}")
    return {"status": "updated", "config": config}

@app.post("/control/reset")
async def reset_chaos():
    """Reset all chaos parameters."""
    state.latency_ms = 0
    state.latency_jitter_ms = 0
    state.error_rate = 0.0
    state.memory_leak_bytes = 0
    state.cpu_burn_ms = 0
    state.leaked_memory.clear() # Be careful clearing this in prod simulation
    logger.info("Chaos config reset")
    return {"status": "reset"}

@app.get("/")
async def root():
    return {"message": "Hello from sim-service", "hostname": os.getenv("HOSTNAME", "unknown")}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.get("/proxy")
async def proxy(url: str):
    """Call an upstream service."""
    with tracer.start_as_current_span("proxy_request") as span:
        span.set_attribute("upstream.url", url)
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(url)
                span.set_attribute("http.status_code", resp.status_code)
                return {"status": resp.status_code, "data": resp.json()}
            except Exception as e:
                logger.error(f"Upstream call failed: url={url}, error={str(e)}", exc_info=True)
                span.set_attribute("error", True)
                span.set_attribute("error.message", str(e))
                raise HTTPException(status_code=502, detail=f"Upstream call failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
