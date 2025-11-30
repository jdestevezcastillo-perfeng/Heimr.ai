/**
 * Stress test for chaos generator
 * Ramps VUs to find breaking points
 */

import { sleep } from 'k6';
import { check } from 'k6';
import { makeWorkRequest, successChecks, resetChaos } from '../lib/helpers.js';

export const options = {
  scenarios: {
    stress: {
      executor: 'ramping-vus',
      startVUs: 1,
      stages: [
        { duration: '2m', target: 20 },  // Ramp up to 20 VUs
        { duration: '3m', target: 50 },  // Ramp up to 50 VUs
        { duration: '2m', target: 100 }, // Ramp up to 100 VUs
        { duration: '2m', target: 100 }, // Hold at 100 VUs
        { duration: '1m', target: 0 },   // Ramp down
      ],
    },
  },
  thresholds: {
    'http_req_duration': ['p(95)<500', 'p(99)<1000'],
    'http_req_failed': ['rate<0.05'], // Less than 5% errors acceptable under stress
  },
};

export function setup() {
  console.log('🔧 Setting up stress test...');
  resetChaos();
  sleep(2);
  return {};
}

export default function () {
  const response = makeWorkRequest();
  
  check(response, successChecks);
  
  sleep(0.1);
}

export function teardown(data) {
  console.log('✅ Stress test completed');
  resetChaos();
}
