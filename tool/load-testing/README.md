# Load Testing

This directory stores load-testing scripts, notes, and result artifacts for SynCode performance benchmarking.

Planned focus areas:
- exam list DB vs Redis
- sync submit vs async submit
- polling vs WebSocket result delivery

Current entry points:
- `run-exam-list.ps1`: beginner-friendly PowerShell wrapper for the exam list benchmark
- `exam-list-db-vs-redis.js`: k6 script for `/friend/exam/semiLogin/list` and `/friend/exam/semiLogin/redis/list`
- `compare-exam-list-results.ps1`: compare two k6 summary JSON files and print a concise result table
- `judge-container-pool.js`: synchronous completed-judge benchmark for comparing per-submission containers with the prewarmed pool
- `judge-async-distributed.js`: end-to-end asynchronous benchmark that submits through RabbitMQ and waits for the final judge result
- `nginx-judge-proxy.conf`: loopback-only proxy configuration used to reach the judge service through an SSH tunnel

## Judge container pool benchmark

Run the same cloud deployment twice with `SANDBOX_EXECUTION_MODE=standalone` and
`SANDBOX_EXECUTION_MODE=pool`. Use the same host, image, question, source code,
container limits, VU count, and duration in both rounds. The endpoint is
synchronous, so `completed_judges` measures fully completed compile-and-run jobs
rather than accepted asynchronous submissions.

Set `DIRECT_JUDGE=true` and point `BASE_URL` at the judge service when the goal
is to isolate sandbox performance. The public `/friend/user/question/run`
workflow also queries Elasticsearch before invoking the judge, so it is useful
for end-to-end testing but can hide the sandbox's actual capacity.

```bash
DIRECT_JUDGE=true \
BASE_URL=http://127.0.0.1:19204 \
QUESTION_ID="$QUESTION_ID" \
SANDBOX_MODE=pool \
VUS=4 \
DURATION=30s \
k6 run \
  --summary-export tool/load-testing/results/judge-direct-pool-vus4.json \
  tool/load-testing/judge-container-pool.js
```

Use a short warm-up run before collecting each formal result. Ramp concurrency
through `1, 4, 8, 12, 20` VUs and stop increasing if the judge failure rate
exceeds 5%, the service health check fails, or the host begins swapping. Record
completed judges per second, P50/P95/P99 latency, error rate, and host CPU/memory.

The cloud result collected on 2026-09-18 is documented in
`results/judge-container-pool-20260918.md`.

## Distributed asynchronous judge benchmark

Point `BASE_URL` at the cloud test stack, not production. The script logs in,
submits to the RabbitMQ-backed endpoint, and polls until each judgment reaches a
final state. `completed_judges` therefore measures completed compile-and-run
work rather than accepted HTTP submissions.

```bash
BASE_URL=http://127.0.0.1:19090 \
QUESTION_ID="$QUESTION_ID" \
VUS=64 \
DURATION=90s \
GRACEFUL_STOP=120s \
k6 run \
  --summary-export tool/load-testing/results/judge-distributed-vus64-90s.json \
  --out json=tool/load-testing/results/judge-distributed-vus64-90s-trace.json \
tool/load-testing/judge-async-distributed.js
```

Set `LANGUAGE=java`, `cpp`, `python`, `go`, or `mixed` for the same two-sum
question. `mixed` assigns one of the four languages to each VU. Before a mixed
benchmark, run `smoke-sandbox-multilang.sh` on every judge host with the exact
sandbox image and memory limit being tested, then send one asynchronous
submission per language through the API. Record the image tag, node count,
container limit, completed judgments during the active window, and drain time.

Use a warm-up before formal runs and capture RabbitMQ queue depth plus `vmstat`
on every judge host. For a fixed-duration test, calculate both completions in
the active submission window and completions during graceful drain. The
three-node cloud result collected on 2026-09-22 is documented in
`results/judge-distributed-20260922.md`.
