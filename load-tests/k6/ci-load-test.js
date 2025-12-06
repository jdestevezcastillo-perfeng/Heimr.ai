// Copyright (c) 2025 Juan Estevez Castillo
// Licensed under AGPL v3. Commercial licenses available.
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');
const auditLogsLatency = new Trend('audit_logs_latency', true);

// Test configuration
// Total Duration: ~10 minutes
export const options = {
  stages: [
    { duration: '10s', target: 5 },    // Warm up (5 VUs)
    { duration: '10s', target: 20 },   // Ramp up to load (20 VUs)
    { duration: '20s', target: 20 },   // Steady state (Hold 20 VUs)
    { duration: '10s', target: 50 },   // Stress spike (50 VUs)
    { duration: '5s', target: 50 },    // Hold spike
    { duration: '5s', target: 0 },     // Cool down
  ],
  thresholds: {
    // Pipeline gating criteria
    http_req_duration: ['p(95)<1000'],   // 95% of requests must be < 1s
    'http_req_duration{name:ListUsers}': ['p(95)<500'], // Stricter for fast endpoint
    'http_req_duration{name:AuditLogs}': ['p(95)<5000'], // Looser for known slow endpoint
    errors: ['rate<0.01'],               // Error rate must be < 1%
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:30808';

export default function () {
  const random = Math.random();
  
  // 1. List Users (High Volume - 50%)
  if (random < 0.5) {
    const res = http.get(`${BASE_URL}/api/users?limit=10`, { tags: { name: 'ListUsers' } });
    check(res, {
      'users: status 200': (r) => r.status === 200,
      'users: has data': (r) => r.json().length > 0,
    });
    errorRate.add(res.status >= 400);

  // 2. Create User (Write Operation - 10%)
  } else if (random < 0.6) {
    const payload = JSON.stringify({
      username: `ci_user_${Date.now()}_${Math.random().toString(36).substr(2, 5)}`,
      email: `test_${Date.now()}@example.com`,
    });
    const params = { 
        headers: { 'Content-Type': 'application/json' },
        tags: { name: 'CreateUser' }
    };
    const res = http.post(`${BASE_URL}/api/users`, payload, params);
    check(res, { 'create: status 200': (r) => r.status === 200 });
    errorRate.add(res.status >= 400);

  // 3. Audit Logs (Heavy Read - 20%)
  } else if (random < 0.8) {
    const start = Date.now();
    const res = http.get(`${BASE_URL}/api/audit-logs?limit=20`, { tags: { name: 'AuditLogs' } });
    auditLogsLatency.add(Date.now() - start);
    check(res, { 'audit: status 200': (r) => r.status === 200 });
    errorRate.add(res.status >= 400);

  // 4. Health Check (Baseline - 20%)
  } else {
    const res = http.get(`${BASE_URL}/health`, { tags: { name: 'HealthCheck' } });
    check(res, { 'health: status 200': (r) => r.status === 200 });
    errorRate.add(res.status >= 400);
  }
  
  sleep(1);
}
