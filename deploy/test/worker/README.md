# Distributed judge workers (test stack)

The existing `onlineoj-test_oj-judge` runs on `101.96.200.76` in Swarm. A
standalone `syncode-test-judge-worker` runs on each of `101.96.200.77` and
`124.223.30.115`, with four local Docker sandboxes per host. All three instances
compete on the realtime `oj-work-queue` and the lower-priority
`oj.judge.batch.queue`. The standalone workers do not publish HTTP ports or
join the Swarm. Do not use test credentials or the test login endpoint against
production.

The old node's `syncode-judge-worker-relay` joins the test backend overlay and
binds RabbitMQ and Redis on host loopback only. On each standalone node,
`syncode-judge-backend-tunnel.service` forwards MySQL, RabbitMQ and Redis to
`172.17.0.1` for its worker container. Each node has a separate SSH key,
restricted on the old node to those three loopback destinations. Each worker
uses `/etc/syncode-judge-worker.env` (mode 600); do not commit or print this
file. Each worker has a 1 CPU / 896 MiB limit. The launcher accepts
`SYNCODE_SANDBOX_POOL_SIZE` and the two current standalone workers use a pool
size of 4. The `124.223.30.115` launcher uses `SYNCODE_WORKER_ID=4` (the `.77`
worker uses 3).
Set `SYNCODE_JUDGE_IMAGE` when launching a canary or rolling back to a retained
image tag; the launcher defaults to the original test image.
For a multi-language canary, set `SYNCODE_SANDBOX_IMAGE` to the installed
sandbox image. `SYNCODE_SANDBOX_MEMORY_BYTES=268435456` sets the tested 256 MiB
container memory limit. The original 100 MB limit kills the Go compiler while
building even a small program.

## Verify

On each standalone node (`sudo docker` on `124.223.30.115`):

```sh
systemctl status syncode-judge-backend-tunnel
docker ps --filter name=syncode-test-judge-worker
docker ps --filter name=oj-sandbox-jdk
```

On the old node, `rabbitmqctl list_queues -p / name consumers` should show three
consumers for each judge input queue. From a checkout with the `syncode-test`
SSH alias, run the smoke test on the old node against its **test** HTTP endpoint:

```sh
ssh syncode-test \
  'TEST_BASE_URL=http://127.0.0.1 TEST_QUESTION_ID=2100393618240483329 bash -s' \
  < deploy/test/worker/smoke-multi-worker.sh
```

Set `TEST_EXAM_ID` to send the same submissions through the batch route. When
it is unset, the script exercises the realtime practice route.

The script uses the allowlisted test student login, submits the existing
two-sum Java solution, and polls each request until it passes. Check `Received
judge message` logs on all three nodes to confirm distribution; a successful
submission alone does not prove which worker consumed it.

On 2026-09-20, 6/6 test submissions passed, split 3/3 between old and new
workers. After restarting the new worker, another 4/4 passed, split 2/2.
RabbitMQ reported two consumers and zero ready/unacknowledged work messages.
On 2026-09-21, after adding `124.223.30.115`, 9/9 submissions passed and each
node consumed 3. After restarting the third worker container, another 6/6
passed, including 2 consumed by that node. RabbitMQ reported three consumers
and zero ready/unacknowledged work messages. These are smoke checks, not
throughput or failover benchmarks.

Later on 2026-09-21, all three workers were upgraded to
`syncode/oj-judge:concurrency-20260921-1444`. Listener concurrency now derives
from each node's local pool size and prefetch is one per consumer. RabbitMQ
reported six active consumers: four for the four-sandbox Swarm worker and one
for each standalone worker. An 18-submission smoke run passed 18/18 and was
distributed 11/5/4 across the three nodes. The Swarm worker's four listener
threads received their first four tasks within a three-millisecond window,
showing that its four local sandboxes were no longer serialized behind one MQ
consumer. The queue finished with zero ready and zero unacknowledged messages.

On 2026-09-22, all three workers were upgraded to
`syncode/oj-judge:local-scheduler-20260922-0835`. Each judge instance now has
one asynchronous RabbitMQ consumer and a bounded `LocalJudgeScheduler` sized
from local execution capacity. RabbitMQ reported three consumers with prefetch
values `4/1/1`. An 18-submission run passed 18/18 and was distributed 11/4/3.
The four-sandbox worker started its first four tasks on
`local-judge-worker-1..4` within five milliseconds, proving that one consumer
can fill the local pool without acting as a judge worker itself.

A fault-injection run then stopped the `.77` process immediately after it
started request `058da49404d047939d9935161d55a9cc`. RabbitMQ recovered the
unacknowledged delivery, and `.115` completed the same request 301.599 seconds
later; all 12/12 submissions passed. The delay matches the current 300-second
Redis lock lease, so message recovery works but crash recovery latency remains
too high. After the run, the work, retry, and dead queues all had zero ready or
unacknowledged messages and the three consumers were active again.

The renewable, owner-checked lease reduced the same crash-recovery path to
44.448 seconds with a 30-second lease, a 10-second renewal interval, and the
existing 15-second retry delay. A recovered stale owner cannot renew or release
the new owner's lock, and conditional final-state updates prevent it from
overwriting a completed result.

Later on 2026-09-22, all three workers and the test runtime were upgraded to
`priority-batch-20260922-1558`. Each instance has one asynchronous MQ entry for
each queue, while both entries feed the same capacity-bounded local scheduler.
RabbitMQ reported three consumers on the realtime queue and three on the batch
queue. A 6-submission realtime smoke run passed 6/6 and was distributed 4/1/1,
matching the nodes' local sandbox capacities.

Twelve submissions carrying an `examId` produced exactly 12 publishes,
deliveries, and acknowledgements on `oj.judge.batch.queue`; a subsequent batch
smoke run passed 6/6. In a mixed-backlog run, 36 batch submissions with 700 ms
of injected execution work started first, followed 1.003 seconds later by 12
realtime submissions. Both groups passed completely. Realtime work finished in
10.330 seconds, 11.220 seconds before the batch group finished, while all batch
work still completed in 22.553 seconds. This validates priority without batch
starvation under this test load.

The two standalone workers were then increased from one to four sandboxes each,
giving the three-node test cluster 12 execution slots. RabbitMQ reported three
consumers per input queue, each with a prefetch of four. A 12-submission smoke
run passed 12/12 and distributed exactly 4/4/4; every instance started work on
`local-judge-worker-1..4`. This verifies concurrent capacity, but it is not a
steady-state TPS measurement.

A subsequent end-to-end k6 benchmark exercised login, asynchronous RabbitMQ
submission, local scheduling, Java compile/run, persistence, and final-result
polling. Across 12/24/48/96 VU 30-second runs, all judgments completed with no
failures. Throughput reached a plateau near 6.3-6.5 completed judgments per
second after 24 VU; additional concurrency increased queueing latency instead
of throughput. A 64 VU, 90-second run completed 590 judgments during the active
window (6.56 TPS) and 405 during its 20-80 second steady middle (6.75 TPS).
At seconds 30 and 70 RabbitMQ held 51 ready and 12 unacknowledged realtime
messages, confirming that all execution slots remained occupied. The queues
fully drained afterward. Detailed methodology, resource samples, and limits
are in `tool/load-testing/results/judge-distributed-20260922.md`.

## Roll Back

Wait for in-flight work to drain, then stop a standalone consumer on its host
without changing the old Swarm service (`sudo` on `124.223.30.115`):

```sh
docker stop syncode-test-judge-worker
systemctl disable --now syncode-judge-backend-tunnel
```

After confirming the remaining workers are healthy, restart that node with
`systemctl enable --now syncode-judge-backend-tunnel` followed by
`docker start syncode-test-judge-worker`. The old node's relay must remain up
while either standalone worker is in use.

## Current Limits

This remains a fixed-size, Java-only pool rather than an elastic multi-language
scheduler. Consumer count is decoupled from execution capacity; prefetch and
the bounded local scheduler limit in-flight work. Lock release verifies
ownership, active jobs renew their leases, database final states are
conditionally updated, and unhealthy pool containers are replaced instead of
bypassing the capacity limit with standalone sandboxes. A batch task is an
independently acknowledged low-priority submission, not a collection of many
submissions in one message. Mixed-language routing, per-language capacity
metrics, elasticity, repeated failover distributions, and controlled 1/2/3-node
scaling-efficiency tests still require dedicated work.
