// Copyright (c) 2025 Juan Estevez Castillo
// Licensed under AGPL v3. Commercial licenses available.
// See LICENSE or https://www.gnu.org/licenses/agpl-3.0.html

// Quick k6 test for the Docker quickstart demo.
// Runs 1 minute against the demo server, outputs JSON for Heimr analysis.

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

const errorRate = new Rate('errors');
const usersLatency = new Trend('users_latency');
const productsLatency = new Trend('products_latency');
const ordersLatency = new Trend('orders_latency');

const BASE_URL = __ENV.BASE_URL || 'http://demo-server:8080';

export const options = {
    stages: [
        { duration: '10s', target: 5 },   // Ramp up
        { duration: '40s', target: 10 },   // Sustain
        { duration: '10s', target: 0 },    // Ramp down
    ],
    thresholds: {
        http_req_duration: ['p(95)<3000'],
        errors: ['rate<0.15'],
    },
};

export default function () {
    const actions = [
        { weight: 40, fn: getUsers },
        { weight: 30, fn: getProducts },
        { weight: 20, fn: createOrder },
        { weight: 10, fn: slowEndpoint },
    ];

    const totalWeight = actions.reduce((sum, a) => sum + a.weight, 0);
    let random = Math.random() * totalWeight;

    for (const action of actions) {
        random -= action.weight;
        if (random <= 0) {
            action.fn();
            break;
        }
    }

    sleep(Math.random() * 1.5 + 0.5);
}

function getUsers() {
    const res = http.get(`${BASE_URL}/api/users`);
    usersLatency.add(res.timings.duration);
    const success = check(res, { 'users 200': (r) => r.status === 200 });
    errorRate.add(!success);
}

function getProducts() {
    const res = http.get(`${BASE_URL}/api/products`);
    productsLatency.add(res.timings.duration);
    const success = check(res, { 'products 200': (r) => r.status === 200 });
    errorRate.add(!success);
}

function createOrder() {
    const payload = JSON.stringify({
        userId: Math.floor(Math.random() * 3) + 1,
        productId: Math.floor(Math.random() * 3) + 1,
        quantity: Math.floor(Math.random() * 5) + 1,
    });
    const res = http.post(`${BASE_URL}/api/orders`, payload, {
        headers: { 'Content-Type': 'application/json' },
    });
    ordersLatency.add(res.timings.duration);
    const success = check(res, { 'order 201': (r) => r.status === 201 });
    errorRate.add(!success);
}

function slowEndpoint() {
    const res = http.get(`${BASE_URL}/api/slow`, { timeout: '10s' });
    const success = check(res, { 'slow 200': (r) => r.status === 200 });
    errorRate.add(!success);
}
