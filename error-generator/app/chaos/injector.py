"""Chaos injection middleware for FastAPI."""
import asyncio
import hashlib
import random
import time
import uuid
from datetime import datetime
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.chaos.state import chaos_state
from app.metrics import (
    chaos_errors_injected_total,
    chaos_latency_injected_seconds,
    chaos_requests_rejected_total,
    chaos_concurrent_requests,
)


class ChaosMiddleware(BaseHTTPMiddleware):
    """Middleware that injects chaos into API requests."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with chaos injection.
        
        Args:
            request: Incoming request
            call_next: Next middleware/handler
            
        Returns:
            Response (possibly modified by chaos)
        """
        # Skip chaos for health and metrics endpoints
        if request.url.path in ["/health", "/metrics"] or request.url.path.startswith("/chaos"):
            return await call_next(request)
        
        # Only apply chaos to /api/* routes
        if not request.url.path.startswith("/api"):
            return await call_next(request)
        
        # Add request ID for correlation
        request_id = str(uuid.uuid4())
        
        # Record request for RPS calculation
        await chaos_state.record_request()
        
        # Get current configuration
        config = await chaos_state.get_config()
        
        # Check concurrency limits
        current_concurrent = await chaos_state.increment_concurrent()
        chaos_concurrent_requests.set(current_concurrent)
        
        try:
            if config.resources.max_concurrent is not None:
                if current_concurrent > config.resources.max_concurrent:
                    chaos_requests_rejected_total.labels(reason="concurrency_limit").inc()
                    return JSONResponse(
                        status_code=503,
                        content={"error": "Service Unavailable", "reason": "Too many concurrent requests"},
                        headers={"X-Request-ID": request_id}
                    )
            
            # Check rate limiting
            if config.errors.rate_limit.enabled:
                allowed = await chaos_state.check_rate_limit()
                if not allowed:
                    chaos_requests_rejected_total.labels(reason="rate_limit").inc()
                    return JSONResponse(
                        status_code=429,
                        content={"error": "Too Many Requests", "reason": "Rate limit exceeded"},
                        headers={
                            "X-Request-ID": request_id,
                            "Retry-After": "1"
                        }
                    )
            
            # Inject errors (before latency to fail fast)
            error_response = await self._inject_errors(config, request_id)
            if error_response:
                return error_response
            
            # Inject latency
            await self._inject_latency(config)
            
            # Perform CPU work if configured
            if config.resources.cpu_work_iterations > 0:
                await self._perform_cpu_work(config.resources.cpu_work_iterations)
            
            # Process the actual request
            response = await call_next(request)
            
            # Add request ID to response
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        finally:
            # Always decrement concurrent counter
            current_concurrent = await chaos_state.decrement_concurrent()
            chaos_concurrent_requests.set(current_concurrent)
    
    async def _inject_errors(self, config, request_id: str) -> Response | None:
        """Inject error responses based on configuration.
        
        Args:
            config: Current chaos configuration
            request_id: Request correlation ID
            
        Returns:
            Error response if error should be injected, None otherwise
        """
        # Check load-dependent errors
        if config.errors.load_dependent.enabled:
            current_rps = await chaos_state.get_current_rps()
            if current_rps > config.errors.load_dependent.threshold_rps:
                if random.random() < config.errors.load_dependent.error_rate_above_threshold:
                    status_code = random.choice(config.errors.status_codes)
                    chaos_errors_injected_total.labels(status_code=status_code).inc()
                    return JSONResponse(
                        status_code=status_code,
                        content={
                            "error": "Service Error",
                            "reason": "Load-dependent error injection",
                            "current_rps": current_rps
                        },
                        headers={"X-Request-ID": request_id}
                    )
        
        # Check random error rate
        if config.errors.rate > 0 and random.random() < config.errors.rate:
            status_code = random.choice(config.errors.status_codes)
            chaos_errors_injected_total.labels(status_code=status_code).inc()
            return JSONResponse(
                status_code=status_code,
                content={
                    "error": "Service Error",
                    "reason": "Random error injection"
                },
                headers={"X-Request-ID": request_id}
            )
        
        return None
    
    async def _inject_latency(self, config):
        """Inject latency based on configuration.
        
        Args:
            config: Current chaos configuration
        """
        total_delay_ms = 0
        
        # Base latency
        base_delay_ms = config.latency.base_ms
        total_delay_ms += base_delay_ms
        if base_delay_ms > 0:
            chaos_latency_injected_seconds.labels(type="base").observe(base_delay_ms / 1000.0)
        
        # Jitter
        if config.latency.jitter_ms > 0:
            jitter = random.uniform(-config.latency.jitter_ms, config.latency.jitter_ms)
            total_delay_ms += jitter
            chaos_latency_injected_seconds.labels(type="jitter").observe(abs(jitter) / 1000.0)
        
        # Degradation over time
        if config.latency.degradation.enabled and config.latency.degradation.start_time:
            elapsed = datetime.utcnow() - config.latency.degradation.start_time
            elapsed_minutes = elapsed.total_seconds() / 60.0
            degradation_ms = min(
                elapsed_minutes * config.latency.degradation.increase_per_minute_ms,
                config.latency.degradation.max_ms
            )
            total_delay_ms += degradation_ms
            if degradation_ms > 0:
                chaos_latency_injected_seconds.labels(type="degradation").observe(degradation_ms / 1000.0)
        
        # Latency spike
        if config.latency.spike.probability > 0 and random.random() < config.latency.spike.probability:
            spike_ms = config.latency.spike.delay_ms
            total_delay_ms += spike_ms
            chaos_latency_injected_seconds.labels(type="spike").observe(spike_ms / 1000.0)
        
        # Bimodal latency
        if config.latency.bimodal.enabled:
            if random.random() < config.latency.bimodal.slow_percentage:
                bimodal_ms = config.latency.bimodal.slow_delay_ms
                total_delay_ms += bimodal_ms
                chaos_latency_injected_seconds.labels(type="bimodal").observe(bimodal_ms / 1000.0)
        
        # Apply the total delay
        if total_delay_ms > 0:
            await asyncio.sleep(total_delay_ms / 1000.0)
    
    async def _perform_cpu_work(self, iterations: int):
        """Perform CPU-intensive work to simulate load.
        
        Args:
            iterations: Number of hash iterations to perform
        """
        # Run in thread pool to avoid blocking event loop
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._cpu_work_sync, iterations)
    
    @staticmethod
    def _cpu_work_sync(iterations: int):
        """Synchronous CPU work (hash iterations).
        
        Args:
            iterations: Number of iterations
        """
        data = b"chaos"
        for _ in range(iterations):
            data = hashlib.sha256(data).digest()
