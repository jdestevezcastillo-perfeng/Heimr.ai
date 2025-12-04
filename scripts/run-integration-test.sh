#!/bin/bash
# Copyright (c) 2025 Juan Estevez Castillo
# Licensed under AGPL v3. Commercial licenses available.
# See LICENSE or https://www.gnu.org/licenses/agpl-3.0.html
#
# Run all load tests and analyze with Heimr
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
RESULTS_DIR="$PROJECT_ROOT/load-tests/results"

MINIKUBE_IP=${MINIKUBE_IP:-$(minikube ip 2>/dev/null || echo "localhost")}
BASE_URL="http://$MINIKUBE_IP:30808"
PROM_URL="http://$MINIKUBE_IP:30909"
LOKI_URL="http://$MINIKUBE_IP:30310"
TEMPO_URL="http://$MINIKUBE_IP:30320"

echo "================================================================"
echo "  Heimr Full Integration Test"
echo "================================================================"
echo ""
echo "Endpoints:"
echo "  App:        $BASE_URL"
echo "  Prometheus: $PROM_URL"
echo "  Loki:       $LOKI_URL"
echo "  Tempo:      $TEMPO_URL"
echo ""

# Create results directory
mkdir -p "$RESULTS_DIR"

# Check if app is reachable
echo "Checking test application..."
if ! curl -s "$BASE_URL/health" | grep -q "ok"; then
    echo "ERROR: Test application not reachable at $BASE_URL"
    echo "Did you run ./scripts/deploy-test-env.sh first?"
    exit 1
fi
echo "✓ Test application is healthy."
echo ""

# Run k6 test
echo "================================================================"
echo "  Running k6 Load Test (8 minutes)"
echo "================================================================"
if command -v k6 &> /dev/null; then
    k6 run "$PROJECT_ROOT/load-tests/k6/load-test.js" \
        -e BASE_URL="$BASE_URL" \
        --out json="$RESULTS_DIR/k6_results.json" \
        2>&1 | tee "$RESULTS_DIR/k6_output.txt"
    echo "✓ k6 test complete. Results in $RESULTS_DIR/k6_results.json"
else
    echo "SKIP: k6 not installed"
fi
echo ""

# Run Locust test (headless mode)
echo "================================================================"
echo "  Running Locust Load Test (5 minutes)"
echo "================================================================"
if command -v locust &> /dev/null; then
    cd "$PROJECT_ROOT/load-tests/locust"
    locust -f locustfile.py --host="$BASE_URL" -u 10 -r 2 -t 5m --headless --csv="$RESULTS_DIR/locust" 2>&1 | tee "$RESULTS_DIR/locust_output.txt"
    echo "✓ Locust test complete. Results in $RESULTS_DIR/locust_*.csv"
else
    echo "SKIP: locust not installed"
fi
echo ""

# Note: JMeter and Gatling require more setup, skip for now
echo "NOTE: JMeter and Gatling tests require additional setup."
echo "      Run them manually if needed."
echo ""

# Analyze with Heimr
echo "================================================================"
echo "  Analyzing Results with Heimr"
echo "================================================================"

# Check for Heimr
HEIMR_CMD=""
if [ -f "$PROJECT_ROOT/.venv/bin/heimr" ]; then
    HEIMR_CMD="$PROJECT_ROOT/.venv/bin/heimr"
elif command -v heimr &> /dev/null; then
    HEIMR_CMD="heimr"
else
    echo "ERROR: Heimr not found. Install with: pip install -e ."
    exit 1
fi

# Analyze k6 results
if [ -f "$RESULTS_DIR/k6_results.json" ]; then
    echo "Analyzing k6 results..."
    $HEIMR_CMD analyze "$RESULTS_DIR/k6_results.json" \
        --prometheus-url "$PROM_URL" \
        --loki-url "$LOKI_URL" \
        --tempo-url "$TEMPO_URL" \
        --explain \
        --llm-url http://localhost:11434/v1 \
        --llm-model llama3.1:8b \
        --output "$RESULTS_DIR/heimr_k6_report.md" || echo "k6 analysis failed (may need LLM)"
    echo ""
fi

# Analyze Locust results
if [ -f "$RESULTS_DIR/locust_stats.csv" ]; then
    echo "Analyzing Locust results..."
    $HEIMR_CMD analyze "$RESULTS_DIR/locust_stats.csv" \
        --format locust \
        --prometheus-url "$PROM_URL" \
        --loki-url "$LOKI_URL" \
        --tempo-url "$TEMPO_URL" \
        --explain \
        --llm-url http://localhost:11434/v1 \
        --llm-model llama3.1:8b \
        --output "$RESULTS_DIR/heimr_locust_report.md" || echo "Locust analysis failed (may need LLM)"
    echo ""
fi

echo "================================================================"
echo "  Complete!"
echo "================================================================"
echo ""
echo "Results saved to: $RESULTS_DIR/"
ls -la "$RESULTS_DIR/"
echo ""
echo "View reports:"
echo "  cat $RESULTS_DIR/heimr_k6_report.md"
echo "  cat $RESULTS_DIR/heimr_locust_report.md"
