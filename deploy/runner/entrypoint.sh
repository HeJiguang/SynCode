#!/usr/bin/env bash

set -euo pipefail

runner_home="${RUNNER_HOME:-/runner}"
template_home="/home/runner"

mkdir -p "${runner_home}"

if [[ ! -f "${runner_home}/config.sh" ]]; then
  cp -a "${template_home}/." "${runner_home}/"
fi

cd "${runner_home}"

if [[ ! -f .runner ]]; then
  : "${RUNNER_NAME:?RUNNER_NAME is required}"
  : "${RUNNER_REPO_URL:?RUNNER_REPO_URL is required}"
  : "${RUNNER_TOKEN:?RUNNER_TOKEN is required on first bootstrap}"

  ./config.sh \
    --unattended \
    --replace \
    --disableupdate \
    --url "${RUNNER_REPO_URL}" \
    --token "${RUNNER_TOKEN}" \
    --name "${RUNNER_NAME}" \
    --labels "${RUNNER_LABELS:-syncode-prod}" \
    --work "${RUNNER_WORKDIR:-_work}"
fi

exec ./run.sh
