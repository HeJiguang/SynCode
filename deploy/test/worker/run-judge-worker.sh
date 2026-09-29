#!/usr/bin/env bash
set -euo pipefail

image="${SYNCODE_JUDGE_IMAGE:-syncode/oj-judge:sha-2c5de55e4352}"
sandbox_image="${SYNCODE_SANDBOX_IMAGE:-}"
name="syncode-test-judge-worker"
env_file="/etc/syncode-judge-worker.env"
worker_id="${SYNCODE_WORKER_ID:-3}"
pool_size="${SYNCODE_SANDBOX_POOL_SIZE:-1}"

if [[ ! "$worker_id" =~ ^[0-9]+$ ]] || ((10#$worker_id > 1023)); then
    echo "SYNCODE_WORKER_ID must be between 0 and 1023" >&2
    exit 1
fi
if [[ ! "$pool_size" =~ ^[1-9][0-9]*$ ]] || ((10#$pool_size > 16)); then
    echo "SYNCODE_SANDBOX_POOL_SIZE must be between 1 and 16" >&2
    exit 1
fi

if [[ ! -f "$env_file" ]]; then
    echo "Missing $env_file" >&2
    exit 1
fi
if ! docker image inspect "$image" >/dev/null 2>&1; then
    echo "Missing image $image" >&2
    exit 1
fi
if [[ -n "$sandbox_image" ]] && ! docker image inspect "$sandbox_image" >/dev/null 2>&1; then
    echo "Missing sandbox image $sandbox_image" >&2
    exit 1
fi
if docker container inspect "$name" >/dev/null 2>&1; then
    echo "Container $name already exists" >&2
    exit 1
fi

mkdir -p /app/user-code /app/user-code-pool /var/lib/syncode-judge-worker/id-state

sandbox_env=()
if [[ -n "$sandbox_image" ]]; then
    sandbox_env+=(--env "SANDBOX_DOCKER_IMAGE=$sandbox_image")
fi
if [[ -n "${SYNCODE_SANDBOX_MEMORY_BYTES:-}" ]]; then
    sandbox_env+=(--env "SANDBOX_LIMIT_MEMORY=$SYNCODE_SANDBOX_MEMORY_BYTES")
    sandbox_env+=(--env "SANDBOX_LIMIT_MEMORY_SWAP=$SYNCODE_SANDBOX_MEMORY_BYTES")
fi

docker run -d \
    --name "$name" \
    --network bridge \
    --add-host host.docker.internal:host-gateway \
    --cpus 1 \
    --memory 896m \
    --memory-swap 896m \
    --pids-limit 256 \
    --env-file "$env_file" \
    --env SANDBOX_DOCKER_HOST=unix:///var/run/docker.sock \
    --env SANDBOX_DOCKER_POOL_SIZE="$pool_size" \
    "${sandbox_env[@]}" \
    --env SYNCODE_ID_LOGICAL_CLOCK_ENABLED=true \
    --env SYNCODE_ID_LOGICAL_CLOCK_WORKER_ID="$worker_id" \
    --env SYNCODE_ID_LOGICAL_CLOCK_STATE_FILE=/app/id-state/high-watermark.properties \
    --mount type=bind,src=/var/run/docker.sock,dst=/var/run/docker.sock \
    --mount type=bind,src=/app/user-code,dst=/app/user-code \
    --mount type=bind,src=/app/user-code-pool,dst=/app/user-code-pool \
    --mount type=bind,src=/var/lib/syncode-judge-worker/id-state,dst=/app/id-state \
    --health-cmd 'curl --fail --silent http://localhost:9204/actuator/health >/dev/null' \
    --health-interval 30s \
    --health-timeout 5s \
    --health-start-period 60s \
    --health-retries 5 \
    --log-opt max-size=20m \
    --log-opt max-file=3 \
    "$image"
