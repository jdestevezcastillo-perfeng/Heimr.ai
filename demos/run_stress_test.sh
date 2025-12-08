#!/bin/bash
# Stress Test with Error Injection
# Duration: 30 minutes with periodic chaos injection

set -e

API_URL="${API_URL:-http://localhost:8080}"
DURATION_MINUTES="${DURATION_MINUTES:-30}"
RESULTS_DIR="load-tests/results"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RESULT_FILE="${RESULTS_DIR}/stress_test_${TIMESTAMP}.json"

echo "=============================================="
echo "🔥 STRESS TEST WITH ERROR INJECTION"
echo "=============================================="
echo "API URL: $API_URL"
echo "Duration: ${DURATION_MINUTES} minutes"
echo "Results: $RESULT_FILE"
echo "=============================================="

# Ensure results directory exists
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

# Function to reset injection
reset_injection() {
    echo "🔄 Resetting injection..."
    curl -s "$API_URL/inject/reset" > /dev/null
}

# Chaos schedule (runs in background)
run_chaos() {
    echo "🎭 Starting chaos schedule..."
    
    # Timeline (in minutes from start):
    # 0-3:   Normal (warmup)
    # 3-6:   50ms latency spike
    # 6-9:   Normal
    # 9-12:  5% error rate
    # 12-15: Normal
    # 15-18: 200ms latency + 2% errors
    # 18-21: Normal
    # 21-24: Memory leak simulation (50MB)
    # 24-27: CPU burn (100ms per request)
    # 27-30: Final chaos (150ms latency + 10% errors + 25MB memory)
    
    sleep 180  # 3 min warmup
    inject 50 0 0 0
    
    sleep 180  # 3 min
    reset_injection
    
    sleep 180  # 3 min
    inject 0 0.05 0 0
    
    sleep 180  # 3 min
    reset_injection
    
    sleep 180  # 3 min
    inject 200 0.02 0 0
    
    sleep 180  # 3 min
    reset_injection
    
    sleep 180  # 3 min
    inject 0 0 50 0
    
    sleep 180  # 3 min
    inject 0 0 0 100
    
    sleep 180  # 3 min - final chaos
    inject 150 0.10 25 0
    
    echo "🎭 Chaos schedule complete"
}

# Trap to cleanup on exit
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

// Custom metrics
const errorRate = new Rate('errors');
const injectedErrors = new Counter('injected_errors');
const latencyTrend = new Trend('api_latency');

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8080';
const DURATION = __ENV.DURATION_MINUTES || '30';

export const options = {
    scenarios: {
        // Sustained load
        sustained: {
            executor: 'ramping-vus',
            startVUs: 0,
            stages: [
                { duration: '2m', target: 20 },   // Ramp up
                { duration: '26m', target: 20 },  // Sustained load
                { duration: '2m', target: 0 },    // Ramp down
            ],
        },
        // Spike traffic
        spikes: {
            executor: 'ramping-vus',
            startVUs: 0,
            stages: [
                { duration: '5m', target: 0 },
                { duration: '30s', target: 50 }, // Spike 1
                { duration: '30s', target: 10 },
                { duration: '5m', target: 10 },
                { duration: '30s', target: 40 }, // Spike 2
                { duration: '30s', target: 10 },
                { duration: '5m', target: 10 },
                { duration: '30s', target: 60 }, // Spike 3
                { duration: '30s', target: 10 },
                { duration: '5m', target: 10 },
                { duration: '30s', target: 45 }, // Spike 4
                { duration: '30s', target: 10 },
                { duration: '5m', target: 10 },
                { duration: '1m', target: 0 },
            ],
        },
    },
    thresholds: {
        http_req_duration: ['p(95)<5000'], // Relaxed for chaos testing
        errors: ['rate<0.5'],              // Allow up to 50% errors during chaos
    },
};

export default function () {
    const endpoints = [
        { path: '/api/users', weight: 40 },
        { path: '/api/products', weight: 35 },
        { path: '/api/slow', weight: 5 },
        { path: '/health', weight: 20 },
    ];
    
    // Weighted random selection
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
    
    // Track injected errors specifically
    if (!success && res.body && res.body.includes('injected')) {
        injectedErrors.add(1);
    }
    
    // POST to orders occasionally
    if (Math.random() < 0.1) {
        const orderRes = http.post(`${BASE_URL}/api/orders`, JSON.stringify({
            userId: Math.floor(Math.random() * 3) + 1,
            productId: Math.floor(Math.random() * 3) + 1,
            quantity: Math.floor(Math.random() * 5) + 1,
        }), {
            headers: { 'Content-Type': 'application/json' },
        });
        
        check(orderRes, {
            'order created': (r) => r.status === 201,
        });
    }
    
    sleep(Math.random() * 2 + 0.5); // 0.5-2.5s think time
}
EOF

echo ""
echo "=============================================="
echo "✅ Stress test complete!"
echo "Results saved to: $RESULT_FILE"
echo "=============================================="
