#!/usr/bin/env bash

set -euo pipefail

STACK_ENV_FILE="${STACK_ENV_FILE:-deploy/prod/env/stack.env}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"

if [[ ! -f "$STACK_ENV_FILE" ]]; then
  echo "stack env file not found: $STACK_ENV_FILE" >&2
  exit 1
fi

load_env_file() {
  local env_file="$1"
  while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line%$'\r'}"
    [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
    export "$line"
  done < "$env_file"
}

load_env_file "$STACK_ENV_FILE"

cd "$REPO_ROOT"

DEPLOYMENT_MODE="${DEPLOYMENT_MODE:-microservices}"
MAVEN_SETTINGS_FILE="${MAVEN_SETTINGS_FILE:-}"

maven_args=(-q -DskipTests package)
if [[ -n "$MAVEN_SETTINGS_FILE" ]]; then
  if [[ ! -f "$MAVEN_SETTINGS_FILE" ]]; then
    echo "Maven settings file not found: $MAVEN_SETTINGS_FILE" >&2
    exit 1
  fi
  maven_args=(-s "$MAVEN_SETTINGS_FILE" "${maven_args[@]}")
fi

echo "[build] packaging Java services"
mvn "${maven_args[@]}"

echo "[build] web image -> $WEB_IMAGE"
docker build -f deploy/prod/docker/next-app.Dockerfile --build-arg APP_NAME=web -t "$WEB_IMAGE" .

echo "[build] app image -> $APP_IMAGE"
docker build -f deploy/prod/docker/next-app.Dockerfile --build-arg APP_NAME=app -t "$APP_IMAGE" .

echo "[build] admin image -> $ADMIN_IMAGE"
docker build -f deploy/prod/docker/next-app.Dockerfile --build-arg APP_NAME=admin -t "$ADMIN_IMAGE" .

if [[ "$DEPLOYMENT_MODE" == "compact" ]]; then
  : "${RUNTIME_IMAGE:?RUNTIME_IMAGE is required for compact deployment}"
  echo "[build] compact runtime image -> $RUNTIME_IMAGE"
  docker build -f deploy/prod/docker/java-service.Dockerfile --build-arg JAR_FILE=oj-modules/oj-runtime/target/oj-runtime-1.0-SNAPSHOT-exec.jar -t "$RUNTIME_IMAGE" .
else
  echo "[build] gateway image -> $GATEWAY_IMAGE"
  docker build -f deploy/prod/docker/java-service.Dockerfile --build-arg JAR_FILE=oj-gateway/target/oj-gateway-1.0-SNAPSHOT-exec.jar -t "$GATEWAY_IMAGE" .

  echo "[build] system image -> $SYSTEM_IMAGE"
  docker build -f deploy/prod/docker/java-service.Dockerfile --build-arg JAR_FILE=oj-modules/oj-system/target/oj-system-1.0-SNAPSHOT-exec.jar -t "$SYSTEM_IMAGE" .

  echo "[build] friend image -> $FRIEND_IMAGE"
  docker build -f deploy/prod/docker/java-service.Dockerfile --build-arg JAR_FILE=oj-modules/oj-friend/target/oj-friend-1.0-SNAPSHOT-exec.jar -t "$FRIEND_IMAGE" .

  echo "[build] job image -> $JOB_IMAGE"
  docker build -f deploy/prod/docker/java-service.Dockerfile --build-arg JAR_FILE=oj-modules/oj-job/target/oj-job-1.0-SNAPSHOT-exec.jar -t "$JOB_IMAGE" .
fi

echo "[build] judge image -> $JUDGE_IMAGE"
docker build -f deploy/prod/docker/java-service.Dockerfile --build-arg JAR_FILE=oj-modules/oj-judge/target/oj-judge-1.0-SNAPSHOT-exec.jar -t "$JUDGE_IMAGE" .

echo "[build] oj-agent image -> $AGENT_IMAGE"
docker build -f deploy/prod/docker/oj-agent.Dockerfile -t "$AGENT_IMAGE" .

echo "[build] image build completed"
