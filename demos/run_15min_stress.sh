#!/bin/bash
# 15-Minute Stress Test with Error Injection
# Timeline: 15 minutes with periodic chaos injection

set -e

API_URL="${API_URL:-http://localhost:8080}"
DURATION_MINUTES="15"
RESULTS_DIR="load-tests/results"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RESULT_FILE="${RESULTS_DIR}/stress_test_15min_${TIMESTAMP}.json"

echo "=============================================="
echo "🔥 15-MINUTE STRESS TEST WITH ERROR INJECTION"
echo "=============================================="
echo "API URL: $API_URL"
echo "Duration: ${DURATION_MINUTES} minutes"
echo "Results: $RESULT_FILE"
echo "=============================================="

mkdir -p "$RESULTS_DIR"

# Function to inject errors
inject() {
    local latency=$1
    local error_rate=$2
    local memory=$3
    local cpu=$4
    echo "💉 Injecting: latency=${latency}ms error_rate=${error_rate} memory=${memory}MB cpu=${cpu}ms"
    curl -s "$API_URL/inject?latency=${latency}&error_rate=${error_rate}&memory=${memory}&cpu=${cpu}" > /dev/null
}

reset_injection() {
    echo "🔄 Resetting injection..."
    curl -s "$API_URL/inject/reset" > /dev/null
}

# Chaos schedule
run_chaos() {
    echo "🎭 Starting chaos schedule (15m)..."
    
    # 0-3: Normal (Warmup)
    sleep 180
    
    # 3-6: Latency Spike (200ms)
    inject 200 0 0 0
    sleep 180
    
    # 6-9: Error Rate (5%)
    reset_injection
    inject 0 0.05 0 0
    sleep 180
    
    # 9-12: Memory Leak (50MB) + Latency (50ms)
    reset_injection
    inject 50 0 50 0
    sleep 180
    
    # 12-15: CPU Burn (100ms) - Final Chaos
    reset_injection
    inject 0 0 0 100
    sleep 180
    
    echo "🎭 Chaos schedule complete"
}

cleanup() {
    echo "🧹 Cleaning up..."
    reset_injection
    if [ ! -z "$CHAOS_PID" ]; then
        kill $CHAOS_PID 2>/dev/null || true
    fi
}
trap cleanup EXIT

# Start chaos in background
run_chaos &
CHAOS_PID=$!

# Run k6 stress test
echo "🚀 Starting k6 stress test (${DURATION_MINUTES} min)..."
k6 run \
    --env BASE_URL="$API_URL" \
    --out json="$RESULT_FILE" \
    - <<'EOF'
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

const errorRate = new Rate('errors');
const latencyTrend = new Trend('api_latency');

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8080';

export const options = {
    scenarios: {
        sustained: {
            executor: 'ramping-vus',
            startVUs: 0,
            stages: [
                { duration: '1m', target: 20 },   // Ramp up
                { duration: '13m', target: 20 },  // Sustained load
                { duration: '1m', target: 0 },    // Ramp down
            ],
        },
    },
    thresholds: {
        http_req_duration: ['p(95)<5000'],
        errors: ['rate<0.5'],
    },
};

export default function () {
    const endpoints = [
        { path: '/api/users', weight: 40 },
        { path: '/api/products', weight: 35 },
        { path: '/api/orders', weight: 25 },
    ];
    
    // Pick endpoint
    const totalWeight = endpoints.reduce((sum, e) => sum + e.weight, 0);
    let random = Math.random() * totalWeight;
    let selectedPath = '/api/users';
    for (const endpoint of endpoints) {
        random -= endpoint.weight;
        if (random <= 0) {
            selectedPath = endpoint.path;
            break;
        }
    }
    
    const startTime = Date.now();
    const res = http.get(`${BASE_URL}${selectedPath}`);
    const duration = Date.now() - startTime;
    
    latencyTrend.add(duration);
    
    const success = check(res, {
        'status is 2xx': (r) => r.status >= 200 && r.status < 300,
    });
    
    errorRate.add(!success);
    
    sleep(Math.random() * 0.5 + 0.1); 
}
EOF

echo ""
echo "=============================================="
echo "✅ Stress test complete!"
echo "Results saved to: $RESULT_FILE"
echo "=============================================="
