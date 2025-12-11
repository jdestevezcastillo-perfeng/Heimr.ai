import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
    stages: [
        { duration: '2m', target: 10 },   // Ramp up
        { duration: '26m', target: 10 },  // Sustained load
        { duration: '2m', target: 0 },    // Ramp down
    ],
    thresholds: {
        http_req_duration: ['p(95)<2000'], // 95% of requests should be under 2s
    },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8081';

export default function () {
    // 80% of traffic: Fast endpoint (indexed users table)
    if (Math.random() < 0.8) {
        let res = http.get(`${BASE_URL}/api/users?limit=10`);
        check(res, { 'users status 200': (r) => r.status == 200 });
        sleep(0.5 + Math.random() * 0.5); // 0.5-1s think time
    }
    // 20% of traffic: Slow endpoint (unindexed audit_logs table - THE ISSUE)
    else {
        let res = http.get(`${BASE_URL}/api/audit-logs?limit=50`);
        check(res, { 'audit-logs status 200': (r) => r.status == 200 });
        sleep(0.5 + Math.random() * 0.5);
    }
}
