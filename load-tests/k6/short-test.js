import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '10s', target: 5 },  // Ramp up
    { duration: '20s', target: 5 },  // Hold
    { duration: '5s', target: 0 },   // Ramp down
  ],
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:30808';

export default function () {
  // Hit the users endpoint (which we instrumented manually)
  let res = http.get(`${BASE_URL}/api/users?limit=5`);
  check(res, { 'status was 200': (r) => r.status == 200 });
  sleep(1);
}
