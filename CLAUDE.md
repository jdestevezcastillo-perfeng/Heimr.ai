# AI Performance Test Analysis Tool - Chaos Generator Component

## Project Context

Building an AI-powered Performance Test Analysis tool that ingests k6 and Prometheus data to identify bottlenecks and generate human-readable explanations. This document covers the **Chaos Generator** component — a controllable API service that produces predictable failure modes for testing the analysis pipeline.

## Owner Context

- Senior Performance Engineer (14+ years) transitioning to DevOps/SRE
- Expert in AppDynamics, Splunk, k6, JMeter, production troubleshooting
- Building skills in Kubernetes, AWS, Terraform, cloud-native observability
- Prefers hands-on implementation over theoretical study
- Has RTX 3090 for local AI workloads

## Architecture Overview

```
┌──────────────┐     ┌───────────────────┐     ┌────────────┐
│     k6       │────▶│  Chaos Generator  │     │ Prometheus │
│ (load gen)   │     │   (FastAPI)       │────▶│            │
└──────────────┘     └───────────────────┘     └─────┬──────┘
                                                     │
       ┌─────────────────────────────────────────────┘
       ▼
┌──────────────────┐     ┌─────────────────────┐
│  Data Collector  │────▶│  AI Analysis Engine │
│   (next phase)   │     │   (next phase)      │
└──────────────────┘     └─────────────────────┘
```

## Chaos Generator Specification

### Purpose

A "performance testing victim" API that misbehaves in controllable, educational ways. Produces deterministic failure modes so the analysis tool can be validated against known patterns.

### Tech Stack

- **Framework**: FastAPI (async-native, easy Prometheus integration)
- **Metrics**: prometheus-fastapi-instrumentator
- **Language**: Python 3.11+
- **Containerization**: Docker with docker-compose for local dev

### API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check (always 200, bypasses chaos) |
| `/api/work` | GET/POST | Main endpoint affected by chaos injection |
| `/api/work/{operation}` | GET/POST | Variant endpoints for different "operations" |
| `/chaos/config` | GET | Retrieve current chaos configuration |
| `/chaos/config` | POST | Update chaos configuration |
| `/chaos/scenario/{name}` | POST | Activate a predefined scenario |
| `/chaos/reset` | POST | Reset to healthy baseline |
| `/metrics` | GET | Prometheus metrics endpoint |

### Chaos Configuration Model

```python
{
  "latency": {
    "base_ms": 50,              # Baseline response time
    "jitter_ms": 20,            # Random variance +/-
    "degradation": {
      "enabled": false,
      "start_time": null,       # ISO timestamp when degradation started
      "increase_per_minute_ms": 100,
      "max_ms": 5000
    },
    "spike": {
      "probability": 0.0,       # 0-1, fraction of requests with spike
      "delay_ms": 3000
    },
    "bimodal": {
      "enabled": false,
      "slow_percentage": 0.1,   # 10% of requests are slow
      "slow_delay_ms": 2000
    }
  },
  "errors": {
    "rate": 0.0,                # Probability of random 5xx
    "status_codes": [500, 502, 503],  # Which errors to return
    "rate_limit": {
      "enabled": false,
      "requests_per_second": 100,
      "bucket_size": 10         # Token bucket size
    },
    "load_dependent": {
      "enabled": false,
      "threshold_rps": 50,
      "error_rate_above_threshold": 0.3
    }
  },
  "resources": {
    "max_concurrent": null,     # Connection pool exhaustion simulation
    "current_concurrent": 0,    # Internal counter
    "cpu_work_iterations": 0,   # Hash iterations per request
    "response_size_bytes": 100  # Response payload size
  }
}
```

### Predefined Scenarios

| Scenario Name | Description | Use Case |
|---------------|-------------|----------|
| `healthy` | Baseline: 50ms ± 20ms, no errors | Establish baseline metrics |
| `gradual_degradation` | Latency +100ms/minute, max 5s | Detect slow performance drift |
| `latency_spike` | 10% of requests get 3s delay | Detect p99 anomalies |
| `bimodal_latency` | 90% fast (50ms), 10% slow (2s) | Detect distribution issues |
| `error_spike` | 30% error rate (mixed 5xx) | Detect error rate anomalies |
| `rate_limited` | 429s above 50 RPS | Detect rate limiting patterns |
| `cascade_failure` | Errors + latency increase with load | Detect saturation patterns |
| `intermittent` | Random 5% failures | Detect flaky behavior |
| `connection_exhaustion` | Max 10 concurrent requests | Detect pool exhaustion |
| `cpu_bound` | 100k hash iterations/request | Detect CPU saturation |

### Prometheus Metrics to Expose

Beyond the automatic FastAPI instrumentation, add custom metrics:

```python
# Chaos state metrics
chaos_scenario_active{scenario="name"}     # Gauge: which scenario is active
chaos_config_value{param="name"}           # Gauge: current config values

# Internal counters
chaos_errors_injected_total                # Counter: errors we caused
chaos_latency_injected_seconds             # Histogram: artificial delays
chaos_requests_rejected_total              # Counter: rate limit rejections
chaos_concurrent_requests                  # Gauge: current in-flight requests
```

### Implementation Notes

1. **Middleware-based injection**: Use FastAPI middleware to apply chaos to all `/api/*` routes without polluting business logic

2. **Thread-safe state**: Use `asyncio.Lock` or similar for concurrent access to chaos config and counters

3. **Time-based degradation**: Store `degradation_start_time` and calculate current delay based on elapsed time

4. **Token bucket for rate limiting**: Implement proper token bucket algorithm, not just a counter

5. **Graceful config updates**: Allow updating config without restarting the service

6. **Request correlation**: Add `X-Request-ID` header to responses for tracing

### Docker Compose Setup

Should include:
- Chaos Generator service (this)
- Prometheus (with remote write enabled)
- Grafana (with k6 dashboard pre-loaded)
- Network configuration for service discovery

### k6 Integration

The companion k6 scripts should:
- Use `experimental-prometheus-rw` output to push metrics directly to Prometheus
- Include scenarios that trigger each chaos mode
- Tag requests with `testid` for segmentation
- Include thresholds for baseline validation

### File Structure

```
chaos-generator/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Pydantic settings
│   ├── models.py            # Chaos configuration models
│   ├── chaos/
│   │   ├── __init__.py
│   │   ├── injector.py      # Chaos injection middleware
│   │   ├── scenarios.py     # Predefined scenario definitions
│   │   └── state.py         # Global chaos state management
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── api.py           # /api/* endpoints
│   │   ├── chaos.py         # /chaos/* endpoints
│   │   └── health.py        # /health endpoint
│   └── metrics.py           # Custom Prometheus metrics
├── k6/
│   ├── scenarios/
│   │   ├── baseline.js      # Healthy baseline test
│   │   ├── stress.js        # Stress test
│   │   └── chaos.js         # Chaos scenario test
│   └── lib/
│       └── helpers.js       # Shared k6 utilities
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── prometheus.yml
└── grafana/
    └── dashboards/
        └── k6-dashboard.json
```

## Next Steps After Chaos Generator

1. **Data Collector Pipeline**: Pull metrics from Prometheus, correlate k6 test runs with application metrics
2. **Feature Engineering**: Extract meaningful features for bottleneck detection
3. **AI Analysis Engine**: LLM-based pattern recognition and explanation generation
4. **Feedback Loop**: Validate analysis accuracy against known chaos scenarios

## Development Commands

```bash
# Start the stack
docker-compose up -d

# Run k6 baseline test
k6 run -o experimental-prometheus-rw k6/scenarios/baseline.js

# Trigger a chaos scenario
curl -X POST http://localhost:8000/chaos/scenario/gradual_degradation

# Check current chaos config
curl http://localhost:8000/chaos/config

# Reset to healthy
curl -X POST http://localhost:8000/chaos/reset
```

## Quality Criteria

- All chaos modes must produce detectable patterns in Prometheus metrics
- Response times should be measurable and correlate with injected delays
- Error rates should match configured probabilities within statistical tolerance
- The service should handle at least 1000 RPS under healthy conditions
- Configuration changes should take effect within 1 second
