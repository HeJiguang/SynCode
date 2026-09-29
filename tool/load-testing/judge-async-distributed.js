import http from 'k6/http';
import { check, sleep } from 'k6';
import { Counter, Rate, Trend } from 'k6/metrics';

const baseUrl = (__ENV.BASE_URL || 'http://127.0.0.1:19090').replace(/\/$/, '');
const questionId = __ENV.QUESTION_ID || '';
const vus = Number(__ENV.VUS || 12);
const duration = __ENV.DURATION || '30s';
const gracefulStop = __ENV.GRACEFUL_STOP || '120s';
const pollIntervalSeconds = Number(__ENV.POLL_INTERVAL_SECONDS || 0.5);
const resultTimeoutMillis = Number(__ENV.RESULT_TIMEOUT_MILLIS || 120000);
const language = (__ENV.LANGUAGE || 'java').toLowerCase();
const languages = ['java', 'cpp', 'python', 'go'];

if (!questionId) {
  throw new Error('QUESTION_ID is required');
}
if (language !== 'mixed' && !languages.includes(language)) {
  throw new Error(`Unsupported LANGUAGE=${language}`);
}

const acceptedSubmissions = new Counter('accepted_submissions');
const completedJudges = new Counter('completed_judges');
const resultPolls = new Counter('result_polls');
const timedOutJudges = new Counter('timed_out_judges');
const judgeFailures = new Rate('judge_failures');
const submitDuration = new Trend('submit_duration', true);
const judgeEndToEndDuration = new Trend('judge_end_to_end_duration', true);

export const options = {
  scenarios: {
    async_judges: {
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
    benchmark: 'judge-async-distributed',
  },
};

const sourceCodes = {
  java: `import java.util.*;
public class Main {
    public static void main(String[] args) {
        Scanner s = new Scanner(System.in);
        int n = s.nextInt();
        int[] a = new int[n];
        for (int i = 0; i < n; i++) a[i] = s.nextInt();
        int target = s.nextInt();
        for (int i = 0; i < n; i++) {
            for (int j = i + 1; j < n; j++) {
                if (a[i] + a[j] == target) {
                    System.out.println(i + " " + j);
                    return;
                }
            }
        }
    }
}`,
  cpp: `#include <iostream>
#include <vector>
using namespace std;
int main() {
    int n; cin >> n;
    vector<int> a(n);
    for (int i = 0; i < n; i++) cin >> a[i];
    int target; cin >> target;
    for (int i = 0; i < n; i++) {
        for (int j = i + 1; j < n; j++) {
            if (a[i] + a[j] == target) {
                cout << i << " " << j << "\\n";
                return 0;
            }
        }
    }
}`,
  python: `import sys
data = list(map(int, sys.stdin.buffer.read().split()))
n = data[0]
a = data[1:n + 1]
target = data[n + 1]
for i in range(n):
    for j in range(i + 1, n):
        if a[i] + a[j] == target:
            print(i, j)
            sys.exit(0)`,
  go: `package main
import (
    "bufio"
    "fmt"
    "os"
)
func main() {
    in := bufio.NewReader(os.Stdin)
    var n int
    fmt.Fscan(in, &n)
    a := make([]int, n)
    for i := range a { fmt.Fscan(in, &a[i]) }
    var target int
    fmt.Fscan(in, &target)
    for i := 0; i < n; i++ {
        for j := i + 1; j < n; j++ {
            if a[i] + a[j] == target {
                fmt.Println(i, j)
                return
            }
        }
    }
}`,
};
const programTypes = { java: 0, cpp: 1, go: 2, python: 3 };
const submitBodies = Object.fromEntries(languages.map((item) => [item, JSON.stringify({
  questionId,
  programType: programTypes[item],
  userCode: sourceCodes[item],
})]));

export function setup() {
  const response = http.post(
    `${baseUrl}/friend/user/test-login`,
    JSON.stringify({ email: 'student@syncode.test' }),
    {
      headers: { 'Content-Type': 'application/json' },
      timeout: '15s',
      tags: { endpoint: 'test-login' },
    },
  );
  const payload = parseJson(response);
  const succeeded = check(response, {
    'test login succeeded': (res) =>
      res.status === 200 && payload?.code === 1000 && typeof payload?.data === 'string',
  });
  if (!succeeded) {
    throw new Error(`test login failed, status=${response.status}, code=${payload?.code}`);
  }
  return { token: payload.data };
}

export default function (data) {
  const currentLanguage = language === 'mixed' ? languages[(__VU - 1) % languages.length] : language;
  const headers = {
    Accept: 'application/json',
    Authorization: `Bearer ${data.token}`,
    'Content-Type': 'application/json',
  };
  const startedAt = Date.now();
  const submitResponse = http.post(
    `${baseUrl}/friend/user/question/rabbit/submit`,
    submitBodies[currentLanguage],
    {
      headers,
      timeout: '15s',
      tags: { endpoint: 'async-submit' },
    },
  );
  submitDuration.add(submitResponse.timings.duration);
  const submitPayload = parseJson(submitResponse);
  const requestId = submitPayload?.data?.requestId;
  const accepted = check(submitResponse, {
    'async submission accepted': (res) =>
      res.status === 200
      && submitPayload?.code === 1000
      && typeof requestId === 'string'
      && requestId.length > 0,
  });
  if (!accepted) {
    judgeFailures.add(true);
    sleep(pollIntervalSeconds);
    return;
  }
  acceptedSubmissions.add(1, { language: currentLanguage });

  const query = `questionId=${encodeURIComponent(questionId)}&requestId=${encodeURIComponent(requestId)}`;
  while (Date.now() - startedAt < resultTimeoutMillis) {
    sleep(pollIntervalSeconds);
    const resultResponse = http.get(
      `${baseUrl}/friend/user/question/exe/result?${query}`,
      {
        headers: { Accept: 'application/json', Authorization: headers.Authorization },
        timeout: '15s',
        tags: { endpoint: 'result-poll' },
      },
    );
    resultPolls.add(1);
    const resultPayload = parseJson(resultResponse);
    if (resultResponse.status !== 200 || resultPayload?.code !== 1000) {
      judgeFailures.add(true);
      return;
    }
    if (resultPayload?.data?.pass === 1) {
      completedJudges.add(1, { language: currentLanguage });
      judgeEndToEndDuration.add(Date.now() - startedAt, { language: currentLanguage });
      judgeFailures.add(false, { language: currentLanguage });
      return;
    }
    if (resultPayload?.data?.pass === 0) {
      judgeFailures.add(true);
      return;
    }
  }

  timedOutJudges.add(1);
  judgeFailures.add(true);
}

function parseJson(response) {
  try {
    return response.json();
  } catch (_) {
    return null;
  }
}
