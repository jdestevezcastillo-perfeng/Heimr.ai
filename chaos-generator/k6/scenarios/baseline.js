/**
 * Baseline performance test for chaos generator
 * Tests healthy scenario to establish baseline metrics
 */

import { sleep } from 'k6';
import { check } from 'k6';
import { makeWorkRequest, successChecks, resetChaos } from '../lib/helpers.js';

export const options = {
  scenarios: {
    baseline: {
      executor: 'constant-vus',
      vus: 10,
      duration: '5m',
    },
  },
  thresholds: {
    'http_req_duration{operation:default}': ['p(95)<100', 'p(99)<150'],
    'http_req_failed{operation:default}': ['rate<0.01'], // Less than 1% errors
    'http_reqs': ['rate>50'], // At least 50 RPS
  },
};

export function setup() {
  console.log('🔧 Setting up baseline test...');
  resetChaos();
  sleep(2); // Allow chaos state to stabilize
  return {};
}

export default function () {
  const response = makeWorkRequest();
  
  check(response, {
    ...successChecks,
    'latency under 100ms': (r) => r.timings.duration < 100,
  });
  
  sleep(0.1); // Small delay between requests
}

export function teardown(data) {
  console.log('✅ Baseline test completed');
}
