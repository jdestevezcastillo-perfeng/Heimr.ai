"""Predefined chaos scenario definitions."""
from datetime import datetime
from app.models import ChaosConfig


def get_scenario(name: str) -> ChaosConfig:
    """Get a predefined chaos scenario by name.
    
    Args:
        name: Scenario name
        
    Returns:
        ChaosConfig for the requested scenario
        
    Raises:
        ValueError: If scenario name is not recognized
    """
    scenarios = {
        "healthy": healthy(),
        "gradual_degradation": gradual_degradation(),
        "latency_spike": latency_spike(),
        "bimodal_latency": bimodal_latency(),
        "error_spike": error_spike(),
        "rate_limited": rate_limited(),
        "cascade_failure": cascade_failure(),
        "intermittent": intermittent(),
        "connection_exhaustion": connection_exhaustion(),
        "cpu_bound": cpu_bound(),
    }
    
    if name not in scenarios:
        available = ", ".join(scenarios.keys())
        raise ValueError(f"Unknown scenario '{name}'. Available: {available}")
    
    return scenarios[name]


def list_scenarios() -> list[str]:
    """Get list of available scenario names."""
    return [
        "healthy",
        "gradual_degradation",
        "latency_spike",
        "bimodal_latency",
        "error_spike",
        "rate_limited",
        "cascade_failure",
        "intermittent",
        "connection_exhaustion",
        "cpu_bound",
    ]


def healthy() -> ChaosConfig:
    """Baseline: 50ms ± 20ms, no errors."""
    return ChaosConfig()


def gradual_degradation() -> ChaosConfig:
    """Latency increases by 100ms/minute, max 5s."""
    config = ChaosConfig()
    config.latency.degradation.enabled = True
    config.latency.degradation.start_time = datetime.utcnow()
    config.latency.degradation.increase_per_minute_ms = 100
    config.latency.degradation.max_ms = 5000
    return config


def latency_spike() -> ChaosConfig:
    """10% of requests get 3s delay (p99 anomalies)."""
    config = ChaosConfig()
    config.latency.spike.probability = 0.1
    config.latency.spike.delay_ms = 3000
    return config


def bimodal_latency() -> ChaosConfig:
    """90% fast (50ms), 10% slow (2s) - distribution issues."""
    config = ChaosConfig()
    config.latency.bimodal.enabled = True
    config.latency.bimodal.slow_percentage = 0.1
    config.latency.bimodal.slow_delay_ms = 2000
    return config


def error_spike() -> ChaosConfig:
    """30% error rate (mixed 5xx)."""
    config = ChaosConfig()
    config.errors.rate = 0.3
    config.errors.status_codes = [500, 502, 503]
    return config


def rate_limited() -> ChaosConfig:
    """429s above 50 RPS."""
    config = ChaosConfig()
    config.errors.rate_limit.enabled = True
    config.errors.rate_limit.requests_per_second = 50
    config.errors.rate_limit.bucket_size = 10
    return config


def cascade_failure() -> ChaosConfig:
    """Errors + latency increase with load (above 50 RPS)."""
    config = ChaosConfig()
    config.errors.load_dependent.enabled = True
    config.errors.load_dependent.threshold_rps = 50
    config.errors.load_dependent.error_rate_above_threshold = 0.3
    config.latency.degradation.enabled = True
    config.latency.degradation.start_time = datetime.utcnow()
    config.latency.degradation.increase_per_minute_ms = 200
    config.latency.degradation.max_ms = 3000
    return config


def intermittent() -> ChaosConfig:
    """Random 5% failures (flaky behavior)."""
    config = ChaosConfig()
    config.errors.rate = 0.05
    config.errors.status_codes = [500, 503]
    return config


def connection_exhaustion() -> ChaosConfig:
    """Max 10 concurrent requests (pool exhaustion)."""
    config = ChaosConfig()
    config.resources.max_concurrent = 10
    return config


def cpu_bound() -> ChaosConfig:
    """100k hash iterations/request (CPU saturation)."""
    config = ChaosConfig()
    config.resources.cpu_work_iterations = 100000
    return config
