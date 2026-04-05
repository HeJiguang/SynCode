#!/usr/bin/env bash

set -euo pipefail

STACK_ENV_FILE="${STACK_ENV_FILE:-deploy/prod/env/stack.env}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"

if [[ ! -f "$STACK_ENV_FILE" ]]; then
  echo "stack env file not found: $STACK_ENV_FILE" >&2
  exit 1
fi

set -a
source "$STACK_ENV_FILE"
set +a

cd "$REPO_ROOT"

echo "[build] packaging Java services"
mvn -q -DskipTests package

echo "[build] web image -> $WEB_IMAGE"
docker build -f deploy/prod/docker/next-app.Dockerfile --build-arg APP_NAME=web -t "$WEB_IMAGE" .

echo "[build] app image -> $APP_IMAGE"
docker build -f deploy/prod/docker/next-app.Dockerfile --build-arg APP_NAME=app -t "$APP_IMAGE" .

echo "[build] admin image -> $ADMIN_IMAGE"
docker build -f deploy/prod/docker/next-app.Dockerfile --build-arg APP_NAME=admin -t "$ADMIN_IMAGE" .

echo "[build] gateway image -> $GATEWAY_IMAGE"
docker build -f deploy/prod/docker/java-service.Dockerfile --build-arg JAR_FILE=oj-gateway/target/oj-gateway-1.0-SNAPSHOT.jar -t "$GATEWAY_IMAGE" .

echo "[build] system image -> $SYSTEM_IMAGE"
docker build -f deploy/prod/docker/java-service.Dockerfile --build-arg JAR_FILE=oj-modules/oj-system/target/oj-system-1.0-SNAPSHOT.jar -t "$SYSTEM_IMAGE" .

echo "[build] friend image -> $FRIEND_IMAGE"
docker build -f deploy/prod/docker/java-service.Dockerfile --build-arg JAR_FILE=oj-modules/oj-friend/target/oj-friend-1.0-SNAPSHOT.jar -t "$FRIEND_IMAGE" .

echo "[build] job image -> $JOB_IMAGE"
docker build -f deploy/prod/docker/java-service.Dockerfile --build-arg JAR_FILE=oj-modules/oj-job/target/oj-job-1.0-SNAPSHOT.jar -t "$JOB_IMAGE" .

echo "[build] judge image -> $JUDGE_IMAGE"
docker build -f deploy/prod/docker/java-service.Dockerfile --build-arg JAR_FILE=oj-modules/oj-judge/target/oj-judge-1.0-SNAPSHOT.jar -t "$JUDGE_IMAGE" .

echo "[build] oj-agent image -> $AGENT_IMAGE"
docker build -f deploy/prod/docker/oj-agent.Dockerfile -t "$AGENT_IMAGE" .

echo "[build] image build completed"
