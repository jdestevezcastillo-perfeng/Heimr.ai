import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');

export const options = {
    stages: [
        { duration: '1m', target: 5 },   // Warm up
        { duration: '3m', target: 10 },  // Normal load
        { duration: '2m', target: 20 },  // Spike
        { duration: '3m', target: 10 },  // Recovery
        { duration: '1m', target: 0 },   // Cool down
    ],
    thresholds: {
        http_req_duration: ['p(95)<500'], // 95% of requests should be below 500ms
        errors: ['rate<0.1'],              // Error rate should be below 10%
    },
};

const BASE_URL = 'http://localhost:8000';

export default function () {
    // 70% - API work endpoint (main workload)
    if (Math.random() < 0.7) {
        const res = http.get(`${BASE_URL}/api/work`);
        const success = check(res, {
            'work status 200': (r) => r.status === 200,
            'work response time < 500ms': (r) => r.timings.duration < 500,
        });
        errorRate.add(!success);
    }

    // 20% - Health check (fast)
    else if (Math.random() < 0.9) {
        const res = http.get(`${BASE_URL}/health`);
        check(res, { 'health status 200': (r) => r.status === 200 });
    }

    // 10% - Metrics endpoint
    else {
        const res = http.get(`${BASE_URL}/metrics`);
        check(res, { 'metrics status 200': (r) => r.status === 200 });
    }

    sleep(Math.random() * 2 + 1); // Random sleep 1-3 seconds
}
