// Copyright (c) 2025 Juan Estevez Castillo
// Licensed under AGPL v3. Commercial licenses available.
// See LICENSE or https://www.gnu.org/licenses/agpl-3.0.html

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');
const usersLatency = new Trend('users_latency');
const productsLatency = new Trend('products_latency');
const ordersLatency = new Trend('orders_latency');
const slowLatency = new Trend('slow_latency');

// Configuration
const BASE_URL = __ENV.BASE_URL || 'http://localhost:30808';

export const options = {
    scenarios: {
        // Steady traffic
        steady_load: {
            executor: 'constant-vus',
            vus: 10,
            duration: '4m',
            startTime: '30s',
        },
        // Ramp up/down
        ramp: {
            executor: 'ramping-vus',
            startVUs: 0,
            stages: [
                { duration: '30s', target: 5 },   // Warm up
                { duration: '3m', target: 15 },   // Ramp to peak
                { duration: '1m', target: 5 },    // Cool down
                { duration: '30s', target: 0 },   // Ramp down
            ],
        },
    },
    thresholds: {
        http_req_duration: ['p(95)<2000'],
        errors: ['rate<0.1'],
    },
};

export default function () {
    const actions = [
        { weight: 40, fn: getUsers },
        { weight: 30, fn: getProducts },
        { weight: 15, fn: createOrder },
        { weight: 10, fn: healthCheck },
        { weight: 5, fn: slowEndpoint },
    ];

    // Weighted random selection
    const totalWeight = actions.reduce((sum, a) => sum + a.weight, 0);
    let random = Math.random() * totalWeight;
    
    for (const action of actions) {
        random -= action.weight;
        if (random <= 0) {
            action.fn();
            break;
        }
    }

    sleep(Math.random() * 2 + 0.5); // 0.5-2.5s think time
}

function getUsers() {
    const res = http.get(`${BASE_URL}/api/users`);
    usersLatency.add(res.timings.duration);
    
    const success = check(res, {
        'users status 200': (r) => r.status === 200,
        'users has data': (r) => r.json('users') !== undefined,
    });
    errorRate.add(!success);
}

function getProducts() {
    const res = http.get(`${BASE_URL}/api/products`);
    productsLatency.add(res.timings.duration);
    
    const success = check(res, {
        'products status 200': (r) => r.status === 200,
        'products has data': (r) => r.json('products') !== undefined,
    });
    errorRate.add(!success);
}

function createOrder() {
    const payload = JSON.stringify({
        userId: Math.floor(Math.random() * 3) + 1,
        productId: Math.floor(Math.random() * 3) + 1,
        quantity: Math.floor(Math.random() * 5) + 1,
    });

    const params = {
        headers: { 'Content-Type': 'application/json' },
    };

    const res = http.post(`${BASE_URL}/api/orders`, payload, params);
    ordersLatency.add(res.timings.duration);
    
    const success = check(res, {
        'order created': (r) => r.status === 201,
        'order has id': (r) => r.json('order.id') !== undefined,
    });
    errorRate.add(!success);
}

function healthCheck() {
    const res = http.get(`${BASE_URL}/health`);
    
    check(res, {
        'health status 200': (r) => r.status === 200,
    });
}

function slowEndpoint() {
    const res = http.get(`${BASE_URL}/api/slow`, {
        timeout: '10s',
    });
    slowLatency.add(res.timings.duration);
    
    const success = check(res, {
        'slow status 200': (r) => r.status === 200,
    });
    errorRate.add(!success);
}
