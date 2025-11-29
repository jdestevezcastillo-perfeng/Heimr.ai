"""FastAPI application entry point."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from app.config import settings
from app.chaos.injector import ChaosMiddleware
from app.chaos.state import chaos_state
from app.routes import health, api, chaos
from app.metrics import (
    chaos_scenario_active,
    chaos_config_value,
    chaos_cpu_work_iterations,
    chaos_response_size_bytes,
)


def setup_opentelemetry(app: FastAPI):
    """Configure OpenTelemetry to send traces to Tempo."""
    resource = Resource.create(attributes={
        "service.name": "error-generator",
        "service.version": "1.0.0"
    })
    tracer_provider = TracerProvider(resource=resource)
    # Send traces to Tempo (OTLP gRPC)
    processor = BatchSpanProcessor(OTLPSpanExporter(endpoint="http://tempo:4317", insecure=True))
    tracer_provider.add_span_processor(processor)
    trace.set_tracer_provider(tracer_provider)
    FastAPIInstrumentor.instrument_app(app)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager.
    
    Args:
        app: FastAPI application instance
    """
    # Startup
    print("🚀 Chaos Generator starting up...")
    
    # Initialize to healthy state
    await chaos_state.reset()
    print("✅ Initialized to healthy baseline")
    
    # Update metrics on startup
    await update_chaos_metrics()
    
    yield
    
    # Shutdown
    print("👋 Chaos Generator shutting down...")


async def update_chaos_metrics():
    """Update Prometheus metrics with current chaos state."""
    config = await chaos_state.get_config()
    scenario = await chaos_state.get_active_scenario()
    
    # Update scenario gauge
    if scenario:
        chaos_scenario_active.labels(scenario=scenario).set(1)
    
    # Update config value gauges
    chaos_config_value.labels(parameter="latency_base_ms").set(config.latency.base_ms)
    chaos_config_value.labels(parameter="latency_jitter_ms").set(config.latency.jitter_ms)
    chaos_config_value.labels(parameter="error_rate").set(config.errors.rate)
    chaos_cpu_work_iterations.set(config.resources.cpu_work_iterations)
    chaos_response_size_bytes.set(config.resources.response_size_bytes)


# Create FastAPI application
app = FastAPI(
    title="Chaos Generator",
    description="A controllable API service that produces predictable failure modes for performance testing",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add chaos injection middleware
app.add_middleware(ChaosMiddleware)

# Configure Prometheus instrumentation
if settings.metrics_enabled:
    Instrumentator().instrument(app).expose(app)

# Configure OpenTelemetry
setup_opentelemetry(app)

# Register routers
app.include_router(health.router, tags=["health"])
app.include_router(api.router, tags=["api"])
app.include_router(chaos.router, tags=["chaos"])


@app.get("/")
async def root():
    """Root endpoint with service information.
    
    Returns:
        Service information and available endpoints
    """
    scenario = await chaos_state.get_active_scenario()
    
    return {
        "service": "error-generator",
        "version": "1.0.0",
        "description": "Controllable chaos injection for performance testing",
        "active_scenario": scenario,
        "endpoints": {
            "health": "/health",
            "metrics": "/metrics",
            "api": "/api/work",
            "chaos_config": "/chaos/config",
            "scenarios": "/chaos/scenarios",
            "docs": "/docs"
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level,
        reload=True
    )
