#!/bin/bash
# Copyright (c) 2025 Juan Estevez Castillo
# Licensed under AGPL v3. Commercial licenses available.
#
# Run a chaos scenario: Load Test + Chaos Injection
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
RESULTS_DIR="$PROJECT_ROOT/load-tests/results"

MINIKUBE_IP=${MINIKUBE_IP:-$(minikube ip 2>/dev/null || echo "192.168.49.2")}
BASE_URL="http://$MINIKUBE_IP:30808"

CHAOS_TYPE=${1:-slow}
DURATION=${2:-5m}

echo "================================================================"
echo "  Running Chaos Scenario: $CHAOS_TYPE"
echo "================================================================"
echo "Base URL: $BASE_URL"
echo "Duration: $DURATION"
echo ""

# Ensure chaos is disabled initially
$SCRIPT_DIR/inject-chaos.sh disable
echo ""

# Start k6 load test in background
echo "Starting k6 load test..."
mkdir -p "$RESULTS_DIR"
# Use --out json to generate granular data for Heimr
k6 run "$PROJECT_ROOT/load-tests/k6/load-test.js" \
    -e BASE_URL="$BASE_URL" \
    --out json="$RESULTS_DIR/k6_chaos_${CHAOS_TYPE}.json" \
    2>&1 | tee "$RESULTS_DIR/k6_chaos_${CHAOS_TYPE}.log" &
K6_PID=$!

echo "Load test started (PID: $K6_PID). Waiting 60s for ramp-up..."
sleep 60

# Inject Chaos
echo ">>> INJECTING CHAOS: $CHAOS_TYPE <<<"
case "$CHAOS_TYPE" in
    slow)
        $SCRIPT_DIR/inject-chaos.sh slow --delay-ms 3000
        ;;
    error)
        $SCRIPT_DIR/inject-chaos.sh error --rate 0.3
        ;;
    memory-leak)
        $SCRIPT_DIR/inject-chaos.sh memory-leak
        ;;
    *)
        echo "Unknown chaos type: $CHAOS_TYPE"
        ;;
esac

echo "Chaos injected. Letting test run for 2 minutes..."
sleep 120

# Disable Chaos
echo ">>> DISABLING CHAOS <<<"
$SCRIPT_DIR/inject-chaos.sh disable

echo "Chaos disabled. Waiting for test to complete..."
wait $K6_PID

echo ""
echo "================================================================"
echo "  Scenario Complete"
echo "================================================================"
echo "Results: $RESULTS_DIR/k6_chaos_${CHAOS_TYPE}.json"
echo ""

# Analyze immediately
echo "Analyzing with Heimr..."
heimr analyze "$RESULTS_DIR/k6_chaos_${CHAOS_TYPE}.json" \
    -c "$PROJECT_ROOT/heimr-test.yaml" \
    --output "$RESULTS_DIR/report_chaos_${CHAOS_TYPE}.md"

echo "Report: $RESULTS_DIR/report_chaos_${CHAOS_TYPE}.md"
