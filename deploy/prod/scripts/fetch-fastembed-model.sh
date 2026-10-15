#!/usr/bin/env bash

set -euo pipefail

MODEL_REPOSITORY="Qdrant/bge-small-zh-v1.5"
MODEL_REVISION="46fbe35fd4374a00fee7de77dfddaeb6dd6a2c59"
MODEL_ONNX_SHA256="1294ea4b6331115a353d81f96b85e8c8d7fdcc284453d5b2fab5b016230aad38"
TARGET_DIR="${1:-.deploy-assets/fastembed-model}"

files=(
  config.json
  model_optimized.onnx
  ort_config.json
  special_tokens_map.json
  tokenizer.json
  tokenizer_config.json
  vocab.txt
)

rm -rf "${TARGET_DIR}"
mkdir -p "${TARGET_DIR}"

for file in "${files[@]}"; do
  url="https://huggingface.co/${MODEL_REPOSITORY}/resolve/${MODEL_REVISION}/${file}"
  echo "[fastembed] downloading ${file}"
  curl --fail --location --silent --show-error \
    --retry 5 --retry-all-errors --connect-timeout 20 --max-time 900 \
    --output "${TARGET_DIR}/${file}" "${url}"
  test -s "${TARGET_DIR}/${file}"
done

if command -v sha256sum >/dev/null 2>&1; then
  printf '%s  %s\n' "${MODEL_ONNX_SHA256}" "${TARGET_DIR}/model_optimized.onnx" | sha256sum --check
else
  printf '%s  %s\n' "${MODEL_ONNX_SHA256}" "${TARGET_DIR}/model_optimized.onnx" | shasum -a 256 --check
fi
printf '%s\n' "${MODEL_REVISION}" > "${TARGET_DIR}/REVISION"
echo "[fastembed] staged pinned model ${MODEL_REPOSITORY}@${MODEL_REVISION}"
