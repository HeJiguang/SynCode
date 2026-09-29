import http from 'k6/http';
import { check } from 'k6';
import { Counter, Rate, Trend } from 'k6/metrics';

const baseUrl = (__ENV.BASE_URL || 'http://127.0.0.1:19090').replace(/\/$/, '');
const hostHeader = __ENV.HOST_HEADER || '';
const authToken = __ENV.AUTH_TOKEN || '';
const questionId = __ENV.QUESTION_ID || '';
const directJudge = (__ENV.DIRECT_JUDGE || '').toLowerCase() === 'true';
const mode = __ENV.SANDBOX_MODE || 'unknown';
const vus = Number(__ENV.VUS || 4);
const duration = __ENV.DURATION || '60s';
const gracefulStop = __ENV.GRACEFUL_STOP || '15s';
const requestTimeout = __ENV.REQUEST_TIMEOUT || '30s';

if (!directJudge && !authToken) {
  throw new Error('AUTH_TOKEN is required');
}
if (!directJudge && !questionId) {
  throw new Error('QUESTION_ID is required');
}

const completedJudges = new Counter('completed_judges');
const judgeFailures = new Rate('judge_failures');
const judgeDuration = new Trend('judge_duration', true);

export const options = {
  scenarios: {
    completed_judges: {
      executor: 'constant-vus',
      vus,
      duration,
      gracefulStop,
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.05'],
    judge_failures: ['rate<0.05'],
  },
  summaryTrendStats: ['avg', 'min', 'med', 'p(90)', 'p(95)', 'p(99)', 'max'],
  tags: {
    benchmark: 'judge-container-pool',
    sandbox_mode: mode,
  },
};

const sourceCode = `import java.io.*;
public class Main {
    public static void main(String[] args) throws Exception {
        BufferedReader reader = new BufferedReader(new InputStreamReader(System.in));
        while (reader.readLine() != null) { }
        System.out.print("0");
    }
}`;

const endpoint = directJudge ? '/judge/runJavaCode' : '/friend/user/question/run';
const requestBody = JSON.stringify(directJudge
  ? {
      userId: 900000001,
      questionId: questionId || '2100393701497417730',
      programType: 0,
      userCode: sourceCode,
      inputList: ['1', '2'],
      outputList: ['0', '0'],
    }
  : {
      questionId,
      programType: 0,
      userCode: sourceCode,
      customInputs: [],
    });

export default function () {
  const headers = {
    Accept: 'application/json',
    'Content-Type': 'application/json',
  };
  if (authToken) {
    headers.Authorization = authToken.startsWith('Bearer ') ? authToken : `Bearer ${authToken}`;
  }
  if (hostHeader) {
    headers.Host = hostHeader;
  }

  const response = http.post(`${baseUrl}${endpoint}`, requestBody, {
    headers,
    tags: {
      endpoint,
      sandbox_mode: mode,
    },
    timeout: requestTimeout,
  });

  let payload;
  try {
    payload = response.json();
  } catch (_) {
    payload = null;
  }
  const succeeded = check(response, {
    'HTTP status is 200': (res) => res.status === 200,
    'judge envelope succeeded': () => payload?.code === 1000,
    'all cases executed': () =>
      payload?.data?.runStatus === 'SUCCEED' && payload?.data?.caseResults?.length === 2,
  });

  if (!succeeded) {
    console.error(JSON.stringify({
      status: response.status,
      code: payload?.code ?? null,
      message: payload?.msg ?? payload?.message ?? null,
      runStatus: payload?.data?.runStatus ?? null,
    }));
  }

  judgeFailures.add(!succeeded);
  if (succeeded) {
    completedJudges.add(1);
    judgeDuration.add(response.timings.duration);
  }
}
