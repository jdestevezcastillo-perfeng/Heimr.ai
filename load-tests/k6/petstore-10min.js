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
        http_req_duration: ['p(95)<3000'], // 95% of requests should be below 3000ms
        errors: ['rate<0.1'],              // Error rate should be below 10%
    },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8080';

export default function () {
    const rand = Math.random();

    // 40% - Get users (DB read)
    if (rand < 0.4) {
        const res = http.get(`${BASE_URL}/api/users`);
        check(res, { 'users status 200': (r) => r.status === 200 });
    }

    // 30% - Get products (DB read)
    else if (rand < 0.7) {
        const res = http.get(`${BASE_URL}/api/products`);
        check(res, { 'products status 200': (r) => r.status === 200 });
    }

    // 10% - Create Order (DB Write)
    else if (rand < 0.8) {
        const payload = JSON.stringify({
            userId: Math.floor(Math.random() * 3) + 1,
            productId: Math.floor(Math.random() * 3) + 1,
            quantity: Math.floor(Math.random() * 5) + 1
        });
        const res = http.post(`${BASE_URL}/api/orders`, payload, {
            headers: { 'Content-Type': 'application/json' },
        });
        check(res, { 'create order status 201': (r) => r.status === 201 });
    }

    // 10% - Slow endpoint (DB read with delay)
    else if (rand < 0.9) {
        const res = http.get(`${BASE_URL}/api/slow`);
        check(res, { 'slow status 200': (r) => r.status === 200 });
    }

    // 10% - Health check
    else {
        const res = http.get(`${BASE_URL}/health`);
        check(res, { 'health status 200': (r) => r.status === 200 });
    }

    sleep(1);
}
