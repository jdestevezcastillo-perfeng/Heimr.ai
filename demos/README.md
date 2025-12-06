# Heimr Demo - Multi-Format Analysis

This demo showcases Heimr's ability to analyze performance test results from multiple load testing tools.

## Quick Demo

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
