"""Custom Prometheus metrics for chaos injection."""
from prometheus_client import Counter, Gauge, Histogram

# Chaos scenario tracking
chaos_scenario_active = Gauge(
    'chaos_scenario_active',
    'Currently active chaos scenario',
    ['scenario']
)

# Chaos configuration values
chaos_config_value = Gauge(
    'chaos_config_value',
    'Current chaos configuration parameter values',
    ['parameter']
)

# Chaos injection counters
chaos_errors_injected_total = Counter(
    'chaos_errors_injected_total',
    'Total number of errors injected by chaos',
    ['status_code']
)

chaos_latency_injected_seconds = Histogram(
    'chaos_latency_injected_seconds',
    'Artificial latency injected by chaos in seconds',
    ['type'],  # type: base, jitter, spike, degradation, bimodal
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

chaos_requests_rejected_total = Counter(
    'chaos_requests_rejected_total',
    'Total number of requests rejected by chaos',
    ['reason']  # reason: rate_limit, concurrency_limit
)

chaos_concurrent_requests = Gauge(
    'chaos_concurrent_requests',
    'Current number of concurrent requests being processed'
)

# Request tracking
chaos_cpu_work_iterations = Gauge(
    'chaos_cpu_work_iterations',
    'Number of CPU work iterations per request'
)

chaos_response_size_bytes = Gauge(
    'chaos_response_size_bytes',
    'Response payload size in bytes'
)
