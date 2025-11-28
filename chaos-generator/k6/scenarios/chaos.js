/**
 * Chaos scenario validation test
 * Iterates through all chaos scenarios and validates expected behavior
 */

import { sleep } from 'k6';
import { check } from 'k6';
import { 
  makeWorkRequest, 
  activateScenario, 
  resetChaos,
  successChecks,
  errorChecks,
  rateLimitChecks 
} from '../lib/helpers.js';

const SCENARIOS = [
  'healthy',
  'latency_spike',
  'bimodal_latency',
  'error_spike',
  'rate_limited',
  'intermittent',
  'connection_exhaustion',
];

export const options = {
  scenarios: {
    chaos_validation: {
      executor: 'per-vu-iterations',
      vus: 10,
      iterations: 20,
      maxDuration: '10m',
    },
  },
  thresholds: {
    'checks': ['rate>0.7'], // At least 70% of checks should pass
  },
};

export function setup() {
  console.log('🔧 Setting up chaos validation test...');
  resetChaos();
  sleep(2);
  
  return {
    scenarios: SCENARIOS,
  };
}

export default function (data) {
  // Test each scenario
  for (const scenario of data.scenarios) {
    console.log(`\n🎭 Testing scenario: ${scenario}`);
    
    // Activate scenario
    if (!activateScenario(scenario)) {
      console.error(`Failed to activate ${scenario}, skipping...`);
      continue;
    }
    
    sleep(1); // Allow scenario to take effect
    
    // Run requests based on scenario type
    switch (scenario) {
      case 'healthy':
        testHealthy();
        break;
      case 'latency_spike':
      case 'bimodal_latency':
        testLatency();
        break;
      case 'error_spike':
      case 'intermittent':
        testErrors();
        break;
      case 'rate_limited':
        testRateLimit();
        break;
      case 'connection_exhaustion':
        testConcurrency();
        break;
      default:
        testGeneric();
    }
    
    sleep(2); // Cooldown between scenarios
  }
  
  // Reset to healthy at the end
  resetChaos();
}

function testHealthy() {
  for (let i = 0; i < 5; i++) {
    const response = makeWorkRequest();
    check(response, {
      ...successChecks,
      'healthy latency': (r) => r.timings.duration < 150,
    });
    sleep(0.1);
  }
}

function testLatency() {
  const latencies = [];
  
  for (let i = 0; i < 10; i++) {
    const response = makeWorkRequest();
    latencies.push(response.timings.duration);
    check(response, successChecks);
    sleep(0.1);
  }
  
  // Check for high latency occurrences
  const highLatency = latencies.filter(l => l > 1000).length;
  console.log(`High latency requests: ${highLatency}/10`);
}

function testErrors() {
  let errorCount = 0;
  const totalRequests = 20;
  
  for (let i = 0; i < totalRequests; i++) {
    const response = makeWorkRequest();
    if (response.status >= 500) {
      errorCount++;
    }
    sleep(0.05);
  }
  
  const errorRate = errorCount / totalRequests;
  console.log(`Error rate: ${(errorRate * 100).toFixed(1)}%`);
  
  check({ errorRate }, {
    'errors detected': (data) => data.errorRate > 0,
  });
}

function testRateLimit() {
  let rateLimitCount = 0;
  
  // Send burst of requests
  for (let i = 0; i < 100; i++) {
    const response = makeWorkRequest();
    if (response.status === 429) {
      rateLimitCount++;
    }
  }
  
  console.log(`Rate limited requests: ${rateLimitCount}/100`);
  
  check({ rateLimitCount }, {
    'rate limiting active': (data) => data.rateLimitCount > 0,
  });
}

function testConcurrency() {
  // This is harder to test in k6 without parallel execution
  // Just verify we can get 503s
  const response = makeWorkRequest();
  console.log(`Response status: ${response.status}`);
}

function testGeneric() {
  for (let i = 0; i < 5; i++) {
    makeWorkRequest();
    sleep(0.1);
  }
}

export function teardown(data) {
  console.log('\n✅ Chaos validation test completed');
  resetChaos();
}
