// Copyright (c) 2025 Juan Estevez Castillo
// Licensed under AGPL v3. Commercial licenses available.
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');
const auditLogsLatency = new Trend('audit_logs_latency', true);

// Test configuration
export const options = {
  stages: [
    { duration: '1m', target: 10 },   // Ramp up to 10 VUs
    { duration: '3m', target: 10 },   // Stay at 10 VUs
    { duration: '1m', target: 20 },   // Spike to 20 VUs
    { duration: '2m', target: 20 },   // Stay at 20 VUs  
    { duration: '1m', target: 0 },    // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<2000'],  // 95% of requests < 2s
    errors: ['rate<0.1'],                // Error rate < 10%
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:30808';

export default function () {
  // Scenario weights
  const random = Math.random();
  
  if (random < 0.4) {
    // 40% - List users (fast endpoint)
    const res = http.get(`${BASE_URL}/api/users?limit=10`);
    check(res, {
      'users: status 200': (r) => r.status === 200,
      'users: has data': (r) => r.json().length > 0,
    });
    errorRate.add(res.status >= 400);
    
  } else if (random < 0.6) {
    // 20% - Query audit logs (SLOW endpoint - unindexed!)
    const start = Date.now();
    const res = http.get(`${BASE_URL}/api/audit-logs?limit=50`);
    const latency = Date.now() - start;
    
    check(res, {
      'audit: status 200': (r) => r.status === 200,
    });
    errorRate.add(res.status >= 400);
    auditLogsLatency.add(latency);
    
  } else if (random < 0.8) {
    // 20% - Create user
    const payload = JSON.stringify({
      username: `user_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      email: `test_${Date.now()}@example.com`,
    });
    const params = { headers: { 'Content-Type': 'application/json' } };
    const res = http.post(`${BASE_URL}/api/users`, payload, params);
    
    check(res, {
      'create: status 200': (r) => r.status === 200,
    });
    errorRate.add(res.status >= 400);
    
  } else {
    // 20% - Health check
    const res = http.get(`${BASE_URL}/health`);
    check(res, {
      'health: status 200': (r) => r.status === 200,
    });
    errorRate.add(res.status >= 400);
  }
  
  sleep(0.5 + Math.random());
}

