#!/bin/bash
# Copyright (c) 2025 Juan Estevez Castillo
# Licensed under AGPL v3. Commercial licenses available.
# See LICENSE or https://www.gnu.org/licenses/agpl-3.0.html
#
# Inject chaos into the test application
#

set -e

MINIKUBE_IP=${MINIKUBE_IP:-$(minikube ip 2>/dev/null || echo "localhost")}
BASE_URL="http://$MINIKUBE_IP:30808"

usage() {
    echo "Usage: $0 <chaos_type> [options]"
    echo ""
    echo "Chaos types:"
    echo "  slow        - Inject slow responses (30% of requests)"
    echo "  error       - Inject random errors (30% of requests)"
    echo "  memory-leak - Enable memory leak (1KB per request)"
    echo "  disable     - Disable all chaos"
    echo ""
    echo "Options:"
    echo "  --delay-ms <ms>  - Delay in milliseconds for 'slow' (default: 2000)"
    echo "  --rate <0-1>     - Error rate for 'error' (default: 0.3)"
    echo ""
    echo "Examples:"
    echo "  $0 slow --delay-ms 3000"
    echo "  $0 error --rate 0.5"
    echo "  $0 memory-leak"
    echo "  $0 disable"
}

if [ $# -lt 1 ]; then
    usage
    exit 1
fi

CHAOS_TYPE="$1"
shift

case "$CHAOS_TYPE" in
    slow)
        DELAY_MS=2000
        while [[ $# -gt 0 ]]; do
            case "$1" in
                --delay-ms) DELAY_MS="$2"; shift 2 ;;
                *) echo "Unknown option: $1"; exit 1 ;;
            esac
        done
        echo "Enabling SLOW chaos: ${DELAY_MS}ms delay on 30% of requests..."
        curl -X POST "$BASE_URL/api/chaos/enable-slow?delay_ms=$DELAY_MS" -s | jq .
        echo ""
        echo "✓ Slow chaos enabled. Requests will be delayed by ${DELAY_MS}ms."
        ;;
    
    error)
        RATE=0.3
        while [[ $# -gt 0 ]]; do
            case "$1" in
                --rate) RATE="$2"; shift 2 ;;
                *) echo "Unknown option: $1"; exit 1 ;;
            esac
        done
        echo "Enabling ERROR chaos: ${RATE} rate ($(echo "$RATE * 100" | bc)% of requests)..."
        curl -X POST "$BASE_URL/api/chaos/enable-error?rate=$RATE" -s | jq .
        echo ""
        echo "✓ Error chaos enabled. $(echo "$RATE * 100" | bc | cut -d. -f1)% of requests will return 500."
        ;;
    
    memory-leak)
        echo "Enabling MEMORY LEAK chaos: 1KB per request..."
        curl -X POST "$BASE_URL/api/chaos/enable-memory-leak" -s | jq .
        echo ""
        echo "✓ Memory leak enabled. Each request adds 1KB to memory."
        echo "  Watch memory usage in Grafana or with: kubectl top pod -n heimr-test"
        ;;
    
    disable)
        echo "Disabling ALL chaos..."
        curl -X POST "$BASE_URL/api/chaos/disable-all" -s | jq .
        echo ""
        echo "✓ All chaos disabled."
        ;;
    
    status)
        echo "Checking chaos status..."
        curl -s "$BASE_URL/health" | jq .
        ;;
    
    *)
        echo "Unknown chaos type: $CHAOS_TYPE"
        usage
        exit 1
        ;;
esac

echo ""
echo "Current status:"
curl -s "$BASE_URL/health" | jq '{chaos_slow, chaos_error, chaos_memory_leak}'
