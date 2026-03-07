# Heimr Demo

This demo showcases Heimr's ability to analyze performance test results from multiple load testing tools.

## Docker Quickstart (Recommended)

The fastest way to see Heimr in action. Runs a complete end-to-end demo:
demo API server, k6 load test, Ollama LLM, and Heimr agent analysis.

**Requirements**: Docker with compose v2+, ~8GB RAM, ~3GB disk (model download on first run).

```bash
# Full demo: load test + AI agent analysis (uses local Ollama — no API keys)
docker compose -f docker-compose.quickstart.yml up --build

# Quick analyze only (no LLM, no Ollama — just parses sample data)
docker compose -f docker-compose.quickstart.yml --profile analyze-only up heimr-analyze --build
```

### What happens

1. **demo-server** starts — a Python HTTP API with simulated latency/errors
2. **ollama** starts and pulls `qwen3.5:9b` (~2GB, first run only)
3. **k6** runs a 1-minute load test against the demo server
4. **heimr-agent** analyzes the results with AI and makes a deployment gate decision

### Configuration

Copy `.env.example` to `.env` to customize:

```bash
cp .env.example .env
```

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_MODEL` | `qwen3.5:9b` | Ollama model (`qwen3.5:9b`, `qwen3.5:27b` for better analysis) |
| `GATE_POLICY` | `advisory` | `strict` (REJECT on issues) or `advisory` (WARN only) |
| `HEIMR_CMD` | `agent` | `agent` (AI-powered) or `analyze` (no LLM) |
| `K6_DURATION` | `1m` | Load test duration |
| `K6_VUS` | `10` | Peak virtual users |

### Using cloud LLM instead of Ollama

Set API keys in `.env` and the agent will auto-detect the provider:

```bash
# OpenAI
OPENAI_API_KEY=sk-...

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...
```

---

## Quick Demo (Local Install)

```bash
# Analyze k6 results
python3 heimr/cli.py analyze load-tests/samples/demo_k6.json

# Analyze JMeter results  
python3 heimr/cli.py analyze load-tests/samples/demo_jmeter_10min.jtl

# Analyze Locust results
python3 heimr/cli.py analyze load-tests/samples/demo_locust_10min_stats_history.csv

# Analyze Gatling results
python3 heimr/cli.py analyze load-tests/samples/demo_gatling_10min_simulation.log

# Analyze HAR (browser recording)
python3 heimr/cli.py analyze heimr/tests/fixtures/sample.har
```

## Sample Files

All sample files contain **10 minutes** of synthetic test data (~3000 requests):

| File | Format | Requests | Error Rate | Avg Latency |
|------|--------|----------|------------|-------------|
| `demo_jmeter_10min.jtl` | JMeter CSV | 3000 | ~19% | ~900ms |
| `demo_locust_10min_stats_history.csv` | Locust | 3000 | ~4% | ~800ms |
| `demo_gatling_10min_simulation.log` | Gatling | 3000 | ~4% | ~850ms |
| `sample.har` | HAR (Browser) | 5 | 20% | 1518ms |

## Running Live Tests

### 1. Start Demo Server

```bash
python3 demos/demo_server.py &
```

The server provides these endpoints:
- `GET /api/users` - Fast (50-150ms)
- `GET /api/products` - Medium (80-200ms)
- `POST /api/orders` - Write operation (150-350ms)
- `GET /api/slow` - Slow endpoint (2-5s)
- `GET /api/error` - Returns 500 error
- `GET /health` - Health check

### 2. Run k6 Test

```bash
BASE_URL=http://localhost:8080 k6 run \
  --duration 1m \
  --vus 5 \
  --out json=results.json \
  load-tests/k6/demo-test.js

python3 heimr/cli.py analyze results.json
```

### 3. Record HAR from Browser

1. Open `http://localhost:8080` (or use the frontend if deployed)
2. Open DevTools (F12) → Network tab
3. Click buttons to generate traffic
4. Right-click → "Save all as HAR"
5. Analyze: `python3 heimr/cli.py analyze recording.har`

## Full Demo Workflow

For a complete demo with K8s deployment:

```bash
./demos/run_demo.sh
```

This will:
1. Deploy the 3-tier architecture (Frontend → API → DB)
2. Run k6 and Locust load tests
3. Analyze results with Heimr
4. Generate comparison reports

## Expected Output

Heimr will generate:
- **Console Report**: KPI summary with anomaly detection
- **AI Analysis**: Root cause analysis using LLM
- **Status**: PASS/FAIL based on thresholds

Example:
```
==================================================
HEIMR REPORT (Level 1)
==================================================
Metric                    | Value          
-------------------------------------------
Result                    | FAILED
Duration                  | 600.00 s
Requests                  | 3000
Throughput                | 5.00 req/s
Error Rate                | 19.20%
Latency P50               | 245.00 ms
Latency P95               | 4523.00 ms
Latency P99               | 5356.08 ms
-------------------------------------------
```

## Presentation Tips

1. **Show format flexibility**: Analyze all 4 formats (k6, JMeter, Locust, Gatling, HAR)
2. **Highlight AI analysis**: The LLM-generated root cause analysis
3. **Demonstrate anomaly detection**: 1482 anomalies detected in JMeter sample
4. **Compare results**: Different tools, same insights

## Notes

- Sample files are **synthetic data** for demo purposes
- Real tests would show actual system behavior
- HAR files represent single browser sessions (not load tests)
- k6 is the easiest to run live (no Java/Scala dependencies)

## Grafana Dashboard

A pre-built Grafana dashboard for the demo is available at `demos/grafana-dashboard.json`.

Import steps:
1. Open Grafana → Dashboards → Import.
2. Upload `grafana-dashboard.json`.
3. Select your Prometheus/Loki/Tempo data sources.
4. Save.

When running Heimr, you can embed a Grafana link scoped to the test window:

```bash
heimr analyze results.json \
  --grafana-url http://localhost:3000 \
  --grafana-dashboard-uid heimr-demo \
  --output report.md
```
