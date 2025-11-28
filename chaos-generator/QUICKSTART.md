# Chaos Generator - Quick Reference

## 🚀 Quick Start

```bash
cd chaos-generator
docker compose up -d
```

## 🔗 Access Points

- **Chaos Generator**: <http://localhost:8000>
- **API Docs**: <http://localhost:8000/docs>
- **Prometheus**: <http://localhost:9090>
- **Grafana**: <http://localhost:3000> (admin/admin)

## 🎭 Chaos Scenarios

```bash
# List all scenarios
curl http://localhost:8000/chaos/scenarios

# Activate a scenario
curl -X POST http://localhost:8000/chaos/scenario/latency_spike

# Reset to healthy
curl -X POST http://localhost:8000/chaos/reset

# Check current config
curl http://localhost:8000/chaos/config
```

## 📊 Available Scenarios

| Scenario | Effect |
|----------|--------|
| `healthy` | Baseline (50ms ± 20ms) |
| `latency_spike` | 10% get 3s delay |
| `bimodal_latency` | 90% fast, 10% slow |
| `gradual_degradation` | +100ms/min |
| `error_spike` | 30% errors |
| `intermittent` | 5% random failures |
| `rate_limited` | 429 above 50 RPS |
| `cascade_failure` | Errors + latency with load |
| `connection_exhaustion` | Max 10 concurrent |
| `cpu_bound` | 100k hash iterations |

## 🧪 Testing

```bash
# Run baseline test
k6 run k6/scenarios/baseline.js

# Run stress test
k6 run k6/scenarios/stress.js

# Validate all scenarios
k6 run k6/scenarios/chaos.js

# With Prometheus remote write
k6 run -o experimental-prometheus-rw=http://localhost:9090/api/v1/write \
  k6/scenarios/baseline.js
```

## 📈 Useful Prometheus Queries

```promql
# Request rate
rate(http_requests_total{job="chaos-generator"}[1m])

# P95 latency
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[1m]))

# Error rate
rate(http_requests_total{status=~"5.."}[1m]) / rate(http_requests_total[1m])

# Chaos errors injected
rate(chaos_errors_injected_total[1m])

# Active scenario
chaos_scenario_active
```

## 🛠️ Management

```bash
# View logs
docker compose logs -f chaos-generator

# Restart service
docker compose restart chaos-generator

# Stop stack
docker compose down

# Stop and remove volumes
docker compose down -v
```

## 🐛 Troubleshooting

```bash
# Check service health
curl http://localhost:8000/health

# Check metrics endpoint
curl http://localhost:8000/metrics

# Check Prometheus targets
curl http://localhost:9090/api/v1/targets | jq '.data.activeTargets'

# Check container status
docker compose ps
```
