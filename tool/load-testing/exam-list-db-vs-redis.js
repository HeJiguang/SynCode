import http from 'k6/http';
import { check, sleep } from 'k6';

const baseUrl = __ENV.BASE_URL || 'http://127.0.0.1:19090';
const endpoint = __ENV.ENDPOINT || '/friend/exam/semiLogin/list';
const vus = Number(__ENV.VUS || 50);
const duration = __ENV.DURATION || '60s';
const pauseSeconds = Number(__ENV.PAUSE_SECONDS || 1);

export const options = {
  vus,
  duration,
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<2000'],
  },
  summaryTrendStats: ['avg', 'min', 'med', 'p(90)', 'p(95)', 'p(99)', 'max'],
};

export default function () {
  const url = `${baseUrl}${endpoint}?pageNum=1&pageSize=5&type=1`;
  const response = http.get(url, {
    headers: {
      Accept: 'application/json',
    },
    tags: {
      endpoint,
    },
  });

  check(response, {
    'status is 200': (r) => r.status === 200,
    'body contains rows': (r) => {
      if (!r.body) {
        return false;
      }
      try {
        const payload = JSON.parse(r.body);
        return payload !== null && Array.isArray(payload.rows);
      } catch (_) {
        return false;
      }
    },
  });

  if (pauseSeconds > 0) {
    sleep(pauseSeconds);
  }
}
