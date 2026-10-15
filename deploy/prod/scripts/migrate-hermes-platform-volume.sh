#!/usr/bin/env bash

set -euo pipefail

STACK_NAME="${STACK_NAME:?STACK_NAME is required}"
AGENT_IMAGE="${AGENT_IMAGE:?AGENT_IMAGE is required}"
PROFILE_VOLUME="${STACK_NAME}_hermes_data"
PLATFORM_VOLUME="${STACK_NAME}_hermes_platform_skills"

docker volume create "${PLATFORM_VOLUME}" >/dev/null

source_args=()
if docker volume inspect "${PROFILE_VOLUME}" >/dev/null 2>&1; then
  source_args=(-v "${PROFILE_VOLUME}:/source:ro")
fi

docker run --rm --user 0:0 \
  "${source_args[@]}" \
  -v "${PLATFORM_VOLUME}:/target" \
  "${AGENT_IMAGE}" \
  python -c '
from pathlib import Path
import os
import shutil

source = Path("/source/platform-skills")
target = Path("/target")
if source.is_dir() and not any(target.iterdir()):
    unsafe = [path for path in source.rglob("*") if path.is_symlink()]
    if unsafe:
        raise RuntimeError("legacy platform Skill store contains symbolic links")
    for item in source.iterdir():
        destination = target / item.name
        if item.is_dir():
            shutil.copytree(item, destination, symlinks=False)
        elif item.is_file() and not item.is_symlink():
            shutil.copy2(item, destination, follow_symlinks=False)
for root, directories, files in os.walk(target):
    os.chown(root, 10000, 10000)
    for name in directories + files:
        path = Path(root) / name
        if not path.is_symlink():
            os.chown(path, 10000, 10000)
'

echo "[deploy] Hermes platform Skill volume is ready: ${PLATFORM_VOLUME}"
