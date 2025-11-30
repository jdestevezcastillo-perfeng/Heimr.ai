"""Pydantic models for chaos configuration."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class LatencyDegradationConfig(BaseModel):
    """Configuration for gradual latency degradation over time."""
    enabled: bool = False
    start_time: Optional[datetime] = None
    increase_per_minute_ms: int = Field(default=100, ge=0)
    max_ms: int = Field(default=5000, ge=0)


class LatencySpikeConfig(BaseModel):
    """Configuration for random latency spikes."""
    probability: float = Field(default=0.0, ge=0.0, le=1.0)
    delay_ms: int = Field(default=3000, ge=0)


class BimodalLatencyConfig(BaseModel):
    """Configuration for bimodal latency distribution."""
    enabled: bool = False
    slow_percentage: float = Field(default=0.1, ge=0.0, le=1.0)
    slow_delay_ms: int = Field(default=2000, ge=0)


class LatencyConfig(BaseModel):
    """Latency chaos configuration."""
    base_ms: int = Field(default=50, ge=0, description="Baseline response time in milliseconds")
    jitter_ms: int = Field(default=20, ge=0, description="Random variance +/- in milliseconds")
    degradation: LatencyDegradationConfig = Field(default_factory=LatencyDegradationConfig)
    spike: LatencySpikeConfig = Field(default_factory=LatencySpikeConfig)
    bimodal: BimodalLatencyConfig = Field(default_factory=BimodalLatencyConfig)


class RateLimitConfig(BaseModel):
    """Configuration for rate limiting."""
    enabled: bool = False
    requests_per_second: int = Field(default=100, ge=1)
    bucket_size: int = Field(default=10, ge=1, description="Token bucket size")


class LoadDependentErrorConfig(BaseModel):
    """Configuration for load-dependent error injection."""
    enabled: bool = False
    threshold_rps: int = Field(default=50, ge=1)
    error_rate_above_threshold: float = Field(default=0.3, ge=0.0, le=1.0)


class ErrorsConfig(BaseModel):
    """Error injection configuration."""
    rate: float = Field(default=0.0, ge=0.0, le=1.0, description="Probability of random 5xx errors")
    status_codes: List[int] = Field(default=[500, 502, 503], description="Which error codes to return")
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig)
    load_dependent: LoadDependentErrorConfig = Field(default_factory=LoadDependentErrorConfig)


class ResourcesConfig(BaseModel):
    """Resource constraint configuration."""
    max_concurrent: Optional[int] = Field(default=None, ge=1, description="Max concurrent requests (None = unlimited)")
    current_concurrent: int = Field(default=0, ge=0, description="Internal counter for concurrent requests")
    cpu_work_iterations: int = Field(default=0, ge=0, description="Hash iterations per request for CPU simulation")
    response_size_bytes: int = Field(default=100, ge=0, description="Response payload size in bytes")


class ChaosConfig(BaseModel):
    """Complete chaos configuration."""
    latency: LatencyConfig = Field(default_factory=LatencyConfig)
    errors: ErrorsConfig = Field(default_factory=ErrorsConfig)
    resources: ResourcesConfig = Field(default_factory=ResourcesConfig)

    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "latency": {
                    "base_ms": 50,
                    "jitter_ms": 20,
                    "degradation": {
                        "enabled": False,
                        "start_time": None,
                        "increase_per_minute_ms": 100,
                        "max_ms": 5000
                    },
                    "spike": {
                        "probability": 0.0,
                        "delay_ms": 3000
                    },
                    "bimodal": {
                        "enabled": False,
                        "slow_percentage": 0.1,
                        "slow_delay_ms": 2000
                    }
                },
                "errors": {
                    "rate": 0.0,
                    "status_codes": [500, 502, 503],
                    "rate_limit": {
                        "enabled": False,
                        "requests_per_second": 100,
                        "bucket_size": 10
                    },
                    "load_dependent": {
                        "enabled": False,
                        "threshold_rps": 50,
                        "error_rate_above_threshold": 0.3
                    }
                },
                "resources": {
                    "max_concurrent": None,
                    "current_concurrent": 0,
                    "cpu_work_iterations": 0,
                    "response_size_bytes": 100
                }
            }
        }
