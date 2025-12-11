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
    // 70% of traffic: Fast endpoint (find pets by status - simple query)
    if (Math.random() < 0.7) {
        let res = http.get(`${BASE_URL}/api/v3/pet/findByStatus?status=available`);
        check(res, { 'findByStatus status 200': (r) => r.status == 200 });
        sleep(0.5 + Math.random() * 0.5); // 0.5-1s think time
    }
    // 30% of traffic: Slower endpoint (get pet by ID - simulates DB lookup)
    else {
        const petId = Math.floor(Math.random() * 10) + 1; // Random pet ID 1-10
        let res = http.get(`${BASE_URL}/api/v3/pet/${petId}`);
        check(res, { 'getPet status 200': (r) => r.status == 200 });
        sleep(0.5 + Math.random() * 0.5);
    }
}
