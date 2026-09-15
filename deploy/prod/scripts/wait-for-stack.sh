#!/usr/bin/env bash

set -euo pipefail

STACK_NAME="${STACK_NAME:?STACK_NAME is required}"
TIMEOUT_SECONDS="${STACK_WAIT_TIMEOUT_SECONDS:-600}"
POLL_SECONDS="${STACK_WAIT_POLL_SECONDS:-5}"

if [[ ! "$TIMEOUT_SECONDS" =~ ^[0-9]+$ ]]; then
  echo "[deploy] STACK_WAIT_TIMEOUT_SECONDS must be a non-negative integer" >&2
  exit 1
fi
if [[ ! "$POLL_SECONDS" =~ ^[1-9][0-9]*$ ]]; then
  echo "[deploy] STACK_WAIT_POLL_SECONDS must be a positive integer" >&2
  exit 1
fi

deadline=$((SECONDS + TIMEOUT_SECONDS))

diagnose_stack() {
  local service
  echo "[deploy] current stack services:" >&2
  docker stack services "$STACK_NAME" >&2 || true
  while IFS= read -r service; do
    [[ -z "$service" ]] && continue
    echo "[deploy] tasks for ${service}:" >&2
    docker service ps --no-trunc "$service" >&2 || true
  done < <(docker stack services --format '{{.Name}}' "$STACK_NAME" 2>/dev/null || true)
}

while true; do
  services="$(docker stack services --format '{{.Name}}|{{.Replicas}}' "$STACK_NAME")"
  if [[ -z "$services" ]]; then
    echo "[deploy] stack ${STACK_NAME} has no services yet"
  else
    all_ready=true
    summary=()
    while IFS='|' read -r service replicas; do
      [[ -z "$service" ]] && continue
      current_replicas="${replicas%%/*}"
      desired_replicas="${replicas##*/}"
      update_state="$(docker service inspect --format '{{if .UpdateStatus}}{{.UpdateStatus.State}}{{end}}' "$service")"
      update_state="${update_state:-unchanged}"

      case "$update_state" in
        paused|rollback_started|rollback_paused|rollback_completed)
          echo "[deploy] service ${service} entered failed update state: ${update_state}" >&2
          diagnose_stack
          exit 1
          ;;
      esac

      if [[ "$current_replicas" != "$desired_replicas" || "$update_state" == "updating" ]]; then
        all_ready=false
      fi
      summary+=("${service}=${replicas},${update_state}")
    done <<< "$services"

    if [[ "$all_ready" == true ]]; then
      echo "[deploy] stack ${STACK_NAME} converged: ${summary[*]}"
      exit 0
    fi
    echo "[deploy] waiting for stack ${STACK_NAME}: ${summary[*]}"
  fi

  if (( SECONDS >= deadline )); then
    echo "[deploy] timed out after ${TIMEOUT_SECONDS}s waiting for stack ${STACK_NAME}" >&2
    diagnose_stack
    exit 1
  fi
  sleep "$POLL_SECONDS"
done
