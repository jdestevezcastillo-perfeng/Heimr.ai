# Chaos Generator

A controllable FastAPI service that produces predictable failure modes for performance testing and AI analysis validation.

### Simulators
- **sim-db**: Simulates a PostgreSQL database.
  - Metrics: Connections, Transactions, Cache Hit Ratio, Locks.
  - Chaos: Connection leaks, Table locks, Latency.
- **sim-cache**: Simulates a Redis cache.
  - Metrics: Commands, Memory, Keyspace Hits/Misses.
  - Chaos: Memory leaks, Flush all, Latency.
- **sim-queue**: Simulates a Kafka broker.
  - Metrics: Producer/Consumer rates, Lag, Broker messages.
  - Chaos: Message flooding, Consumer lag injection.
- **sim-inference**: Simulates an ML Inference Service (NVIDIA GPU).
  - Metrics: GPU Temp/Power/Util (DCGM/SMI), Inference Latency/Throughput.
  - Chaos: Compute load (GPU overheat), VRAM fill (OOM), Latency.

### Chaos Controller
Orchestrates chaos scenarios using Custom Resource Definitions (CRDs).
- **Actions**: `latency`, `cpu-burn`, `memory-leak`, `error-injection`, `connection-leak`, `lock-table`, `flush-redis`, `kafka-flood`, `compute-load`, `vram-fill`.

## 🎯 Purpose

The Chaos Generator is a "performance testing victim" API that misbehaves in controllable, educational ways. It produces deterministic failure modes so analysis tools can be validated against known patterns.

## 🏗️ Architecture

```
┌──────────────┐     ┌───────────────────┐     ┌────────────┐
│     k6       │────▶│  Chaos Generator  │     │ Prometheus │
│ (load gen)   │     │   (FastAPI)       │────▶│            │
└──────────────┘     └───────────────────┘     └─────┬──────┘
                                                      │
       ┌──────────────────────────────────────────────┘
       ▼
┌──────────────────┐
│     Grafana      │
│  (dashboards)    │
└──────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- k6 (optional, for load testing)

### Start the Stack

```bash
cd error-generator
docker-compose up -d
```

This starts:
- **Chaos Generator** on http://localhost:8000
- **Prometheus** on http://localhost:9090
- **Grafana** on http://localhost:3000 (admin/admin)

### Verify Installation

```bash
# Check health
curl http://localhost:8000/health

# View available scenarios
curl http://localhost:8000/chaos/scenarios

# Check Grafana dashboard
open http://localhost:3000
```

## 📡 API Endpoints

### Health & Info

- `GET /` - Service information
- `GET /health` - Health check (bypasses chaos)
- `GET /metrics` - Prometheus metrics

### Work Endpoints (Affected by Chaos)

- `GET /api/work` - Simple work endpoint
- `POST /api/work` - Work endpoint with request body
- `GET /api/work/{operation}` - Parameterized work endpoint
- `POST /api/work/{operation}` - Parameterized work with body

### Chaos Control

- `GET /chaos/config` - Get current chaos configuration
- `POST /chaos/config` - Update chaos configuration
- `GET /chaos/scenarios` - List available scenarios
- `POST /chaos/scenario/{name}` - Activate a predefined scenario
- `POST /chaos/reset` - Reset to healthy baseline

## 🎭 Chaos Scenarios

| Scenario | Description | Use Case |
|----------|-------------|----------|
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

## 🧪 Usage Examples

### Activate a Chaos Scenario

```bash
# Activate latency spike scenario
curl -X POST http://localhost:8000/chaos/scenario/latency_spike

# Check current configuration
curl http://localhost:8000/chaos/config

# Reset to healthy
curl -X POST http://localhost:8000/chaos/reset
```

### Custom Chaos Configuration

```bash
curl -X POST http://localhost:8000/chaos/config \
  -H "Content-Type: application/json" \
  -d '{
    "latency": {
      "base_ms": 100,
      "jitter_ms": 50
    },
    "errors": {
      "rate": 0.1,
      "status_codes": [500, 503]
    }
  }'
```

### Run k6 Tests

```bash
# Baseline test (5 minutes, 10 VUs)
k6 run k6/scenarios/baseline.js

# Stress test (ramp to 100 VUs)
k6 run k6/scenarios/stress.js

# Chaos validation (test all scenarios)
k6 run k6/scenarios/chaos.js
```

### With Prometheus Remote Write

```bash
k6 run -o experimental-prometheus-rw=http://localhost:9090/api/v1/write \
  k6/scenarios/baseline.js
```

## 📊 Monitoring

### Grafana Dashboard

1. Open http://localhost:3000
2. Login with `admin/admin`
3. Navigate to "Chaos Generator Dashboard"

The dashboard shows:
- Active chaos scenario
- Request rate and latency percentiles
- Error rates (5xx, 429)
- Concurrent requests
- Chaos-specific metrics (injected errors, latency)

### Prometheus Queries

```promql
# Request rate
rate(http_requests_total{job="error-generator"}[1m])

# P95 latency
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[1m]))

# Error rate
rate(http_requests_total{status=~"5.."}[1m]) / rate(http_requests_total[1m])

# Chaos errors injected
rate(chaos_errors_injected_total[1m])
```

## 🔧 Development

### Local Development (without Docker)

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Run the service
python -m app.main
```

### Environment Variables

Create a `.env` file:

```env
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=info
CORS_ORIGINS=["*"]
METRICS_ENABLED=true
```

## 📁 Project Structure

```
error-generator/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Pydantic settings
│   ├── models.py            # Chaos configuration models
│   ├── metrics.py           # Custom Prometheus metrics
│   ├── chaos/
│   │   ├── __init__.py
│   │   ├── injector.py      # Chaos injection middleware
│   │   ├── scenarios.py     # Predefined scenario definitions
│   │   └── state.py         # Global chaos state management
│   └── routes/
│       ├── __init__.py
│       ├── api.py           # /api/* endpoints
│       ├── chaos.py         # /chaos/* endpoints
│       └── health.py        # /health endpoint
├── k6/
│   ├── scenarios/
│   │   ├── baseline.js      # Healthy baseline test
│   │   ├── stress.js        # Stress test
│   │   └── chaos.js         # Chaos scenario test
│   └── lib/
│       └── helpers.js       # Shared k6 utilities
├── grafana/
│   ├── dashboards/
│   │   └── chaos-dashboard.json
│   └── provisioning/
│       ├── datasources/
│       │   └── prometheus.yml
│       └── dashboards/
│           └── default.yml
├── docker-compose.yml
├── Dockerfile
├── prometheus.yml
├── requirements.txt
└── README.md
```

## 🎓 Educational Use

This project is designed for learning:

1. **Performance Engineering**: Understand common failure modes
2. **Observability**: Practice metrics collection and analysis
3. **Load Testing**: Learn k6 and performance testing patterns
4. **AI/ML**: Generate training data for bottleneck detection models

## 🔍 Quality Criteria

- ✅ All chaos modes produce detectable patterns in Prometheus
- ✅ Response times correlate with injected delays (±10% tolerance)
- ✅ Error rates match configured probabilities (±5% tolerance)
- ✅ Service handles 1000 RPS under healthy conditions
- ✅ Configuration changes take effect within 1 second

## 🐛 Troubleshooting

### Service won't start

```bash
# Check logs
docker-compose logs error-generator

# Rebuild
docker-compose up --build
```

### Prometheus not scraping

```bash
# Check Prometheus targets
open http://localhost:9090/targets

# Verify service is exposing metrics
curl http://localhost:8000/metrics
```

### Grafana dashboard not loading

```bash
# Check Grafana logs
docker-compose logs grafana

# Verify datasource
curl http://localhost:3000/api/datasources
```

## 📝 License

MIT

## 🤝 Contributing

This is an educational project. Feel free to fork and experiment!

## 🔗 Next Steps

1. **Data Collector Pipeline**: Pull metrics from Prometheus
2. **Feature Engineering**: Extract meaningful features
3. **AI Analysis Engine**: LLM-based pattern recognition
4. **Feedback Loop**: Validate analysis accuracy
