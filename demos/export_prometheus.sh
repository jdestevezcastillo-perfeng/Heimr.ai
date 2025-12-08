#!/bin/bash
# Export metrics from Prometheus for Heimr analysis

# Calculate time range (last 35 minutes to cover the test)
END_TIME=$(date +%s)
START_TIME=$((END_TIME - 2100))  # 35 minutes ago

OUTPUT_DIR="load-tests/results"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "Exporting Prometheus metrics from $(date -d @$START_TIME) to $(date -d @$END_TIME)..."

# Export key metrics
curl -s "http://localhost:9091/api/v1/query_range?query=http_requests_total&start=${START_TIME}&end=${END_TIME}&step=15s" > /tmp/prom_requests.json
curl -s "http://localhost:9091/api/v1/query_range?query=http_requests_failed_total&start=${START_TIME}&end=${END_TIME}&step=15s" > /tmp/prom_errors.json
curl -s "http://localhost:9091/api/v1/query_range?query=http_request_duration_seconds_sum&start=${START_TIME}&end=${END_TIME}&step=15s" > /tmp/prom_duration.json
curl -s "http://localhost:9091/api/v1/query_range?query=injection_enabled&start=${START_TIME}&end=${END_TIME}&step=15s" > /tmp/prom_injection.json
curl -s "http://localhost:9091/api/v1/query_range?query=injection_latency_ms&start=${START_TIME}&end=${END_TIME}&step=15s" > /tmp/prom_latency_inj.json
curl -s "http://localhost:9091/api/v1/query_range?query=injection_memory_mb&start=${START_TIME}&end=${END_TIME}&step=15s" > /tmp/prom_memory.json

# Combine into Heimr-compatible format
python3 << 'EOF'
import json
import sys

def load_prom(filename):
    try:
        with open(filename) as f:
            data = json.load(f)
            if data.get('status') == 'success':
                return data.get('data', {}).get('result', [])
    except:
        pass
    return []

# Build combined metrics structure
metrics = {
    "cpu_usage": [],  # We'll add request rate as a proxy
    "memory_usage": []
}

# Add request metrics (treating as a signal)
requests = load_prom('/tmp/prom_requests.json')
if requests:
    for r in requests:
        endpoint = r.get('metric', {}).get('endpoint', 'unknown')
        values = r.get('values', [])
        metrics[f"requests_{endpoint}"] = [{
            "metric": {"endpoint": endpoint},
            "values": values
        }]

# Add error metrics
errors = load_prom('/tmp/prom_errors.json')
if errors:
    for r in errors:
        endpoint = r.get('metric', {}).get('endpoint', 'unknown')
        values = r.get('values', [])
        metrics[f"errors_{endpoint}"] = [{
            "metric": {"endpoint": endpoint},
            "values": values
        }]

# Add injection metrics (simulate as "resource" metrics for Heimr)
injection = load_prom('/tmp/prom_injection.json')
if injection:
    metrics["cpu_usage"] = injection  # Treat injection_enabled as CPU proxy

latency_inj = load_prom('/tmp/prom_latency_inj.json')
if latency_inj:
    metrics["memory_usage"] = latency_inj  # Treat latency injection as memory proxy

# Output
with open('load-tests/results/prometheus_stress_test.json', 'w') as f:
    json.dump(metrics, f, indent=2)

print(f"Exported {len(metrics)} metric types to prometheus_stress_test.json")
EOF

echo "Done!"
