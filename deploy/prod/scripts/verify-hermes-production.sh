#!/usr/bin/env bash

set -euo pipefail

STACK_NAME="${STACK_NAME:-onlineoj-prod}"
VERIFY_HERMES_LIVE_RUN="${VERIFY_HERMES_LIVE_RUN:-true}"
VERIFY_HERMES_USER_ID="${VERIFY_HERMES_USER_ID:-900000000000000001}"
TOOLS_SERVICE="${STACK_NAME}_oj-agent-tools"
HERMES_SERVICE="${STACK_NAME}_hermes"

container_for_service() {
  local service="$1"
  docker ps \
    --filter "label=com.docker.swarm.service.name=${service}" \
    --format '{{.ID}}' \
    | head -n 1
}

tools_container="$(container_for_service "$TOOLS_SERVICE")"
hermes_container="$(container_for_service "$HERMES_SERVICE")"
if [[ -z "$tools_container" || -z "$hermes_container" ]]; then
  echo "[verify-hermes] running Hermes containers were not found for stack ${STACK_NAME}" >&2
  exit 1
fi

echo "[verify-hermes] checking readiness, profile policy, memory provider, platform catalog and Elasticsearch"
docker exec -i \
  -e "VERIFY_HERMES_USER_ID=${VERIFY_HERMES_USER_ID}" \
  "$tools_container" python - <<'PY'
from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.request import Request, urlopen

import yaml

from app.learning_memory.search import LearningMemoryIndex
from app.skill_governance.search import EmbeddingClient, ElasticsearchSkillIndex


def read_json(request: Request | str, timeout: float = 15.0) -> dict:
    with urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read(512_000))
    if not isinstance(payload, dict):
        raise RuntimeError("expected a JSON object")
    return payload


ready = read_json("http://127.0.0.1:8016/ready")
if ready.get("status") != "READY":
    raise RuntimeError(f"oj-agent-tools is not ready: {ready}")

user_id = os.environ["VERIFY_HERMES_USER_ID"]
if not user_id.isdecimal():
    raise RuntimeError("VERIFY_HERMES_USER_ID must be numeric")
profile = f"syncode-u{user_id}"
provision_key = os.environ["SYNCODE_HERMES_PROVISION_KEY"]
request = Request(
    "http://127.0.0.1:8016/internal/profiles/ensure",
    data=json.dumps({"user_id": user_id, "profile": profile}).encode("utf-8"),
    headers={
        "Authorization": f"Bearer {provision_key}",
        "Content-Type": "application/json",
    },
    method="POST",
)
provisioned = read_json(request)
if provisioned.get("profile") != profile:
    raise RuntimeError(f"unexpected provision response: {provisioned}")

memory_request = Request(
    "http://127.0.0.1:8016/internal/learning-memory/recall",
    data=json.dumps({"query": "检查生产学习记忆召回"}, ensure_ascii=False).encode("utf-8"),
    headers={
        "Authorization": f"Bearer {os.environ['SYNCODE_MCP_SERVICE_KEY']}",
        "X-SynCode-Hermes-Profile": profile,
        "Content-Type": "application/json",
    },
    method="POST",
)
memory_result = read_json(memory_request, timeout=30)
if memory_result.get("memory_domain") != "syncode_learning":
    raise RuntimeError(f"learning-memory recall returned an invalid payload: {memory_result}")

config_path = Path("/var/lib/hermes/profiles") / profile / "config.yaml"
config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
if config.get("platform_toolsets", {}).get("api_server") != ["memory", "syncode"]:
    raise RuntimeError("profile exposes toolsets other than memory + syncode")
memory = config.get("memory", {})
if memory.get("provider") != "syncode-learning-memory":
    raise RuntimeError("SynCode learning memory is not the Hermes core memory provider")
external_dirs = config.get("skills", {}).get("external_dirs")
if external_dirs != ["/opt/platform-data/platform-skills"]:
    raise RuntimeError(f"unexpected platform Skill mount: {external_dirs}")

provider = Path("/var/lib/hermes/profiles") / profile / "plugins/syncode-learning-memory/plugin.yaml"
if not provider.is_file():
    raise RuntimeError("profile does not contain the SynCode learning-memory provider")

platform_root = Path(os.environ["SYNCODE_PLATFORM_SKILL_STORE"])
skill_names = {
    path.parent.name
    for path in platform_root.rglob("SKILL.md")
    if ".archive" not in path.parts
}
required_skills = {
    "syncode-tutor",
    "syncode-diagnosis",
    "syncode-training-plan",
    "syncode-learning-memory",
}
missing = sorted(required_skills - skill_names)
if missing:
    raise RuntimeError(f"platform Skill catalog is missing: {', '.join(missing)}")
probe = platform_root / ".production-write-probe"
probe.write_text("ready", encoding="ascii")
probe.unlink()

elasticsearch_url = os.environ["SYNCODE_ELASTICSEARCH_URL"].rstrip("/")
cluster = read_json(elasticsearch_url)
if not cluster.get("version"):
    raise RuntimeError("Elasticsearch did not return cluster version metadata")

embedder = EmbeddingClient()
vector = embedder.embed(["SynCode production embedding verification"])[0]
if len(vector) != embedder.dimensions:
    raise RuntimeError("embedding verification returned the wrong vector dimensions")
skill_index = ElasticsearchSkillIndex(embedder=embedder)
memory_index = LearningMemoryIndex(embedder=embedder)
skill_index.ensure_index()
memory_index.ensure_index()
for index_name in (skill_index.index_name, memory_index.index_name):
    mapping = read_json(f"{elasticsearch_url}/{index_name}/_mapping")
    dimensions = (
        mapping.get(index_name, {})
        .get("mappings", {})
        .get("properties", {})
        .get("content_vector", {})
        .get("dims")
    )
    if dimensions != embedder.dimensions:
        raise RuntimeError(
            f"Elasticsearch index {index_name} has dimensions={dimensions}, "
            f"expected {embedder.dimensions}"
        )

heartbeat_request = Request(
    "http://127.0.0.1:8016/internal/skill-governance/heartbeat",
    data=b"{}",
    headers={
        "Authorization": f"Bearer {provision_key}",
        "Content-Type": "application/json",
    },
    method="POST",
)
heartbeat = read_json(heartbeat_request, timeout=180)
if heartbeat.get("status") != "completed":
    raise RuntimeError(f"Skill governance heartbeat did not complete: {heartbeat}")

print(
    f"[verify-hermes] profile={profile} provider=syncode-learning-memory "
    f"platform_skills={len(skill_names)} embedding_dimensions={len(vector)} "
    f"elasticsearch={cluster.get('version', {}).get('number', 'unknown')} "
    f"governance_heartbeat={heartbeat.get('heartbeat_id')}"
)
PY

echo "[verify-hermes] checking that Hermes cannot write the platform Skill catalog"
mount_writable="$(docker inspect --format '{{range .Mounts}}{{if eq .Destination "/opt/platform-data/platform-skills"}}{{.RW}}{{end}}{{end}}' "$hermes_container")"
if [[ "$mount_writable" != "false" ]]; then
  echo "[verify-hermes] platform Skill mount is missing or not read-only" >&2
  exit 1
fi
if docker exec "$hermes_container" sh -ec '
  test -d /opt/platform-data/platform-skills
  python -c "from pathlib import Path; Path('/opt/platform-data/platform-skills/.production-write-probe').write_text('unsafe')"
' >/dev/null 2>&1; then
  docker exec "$hermes_container" rm -f /opt/platform-data/platform-skills/.production-write-probe >/dev/null 2>&1 || true
  echo "[verify-hermes] Hermes can write the platform Skill catalog" >&2
  exit 1
fi

if [[ "$VERIFY_HERMES_LIVE_RUN" == "true" ]]; then
  echo "[verify-hermes] running a real Hermes + core-memory + MCP + SSE acceptance turn"
  docker exec -i \
    -e "VERIFY_HERMES_USER_ID=${VERIFY_HERMES_USER_ID}" \
    "$tools_container" python - <<'PY'
from __future__ import annotations

import json
import os
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import uuid4


user_id = os.environ["VERIFY_HERMES_USER_ID"]
profile = f"syncode-u{user_id}"
api_key = os.environ["HERMES_API_SERVER_KEY"]
base_url = f"http://hermes:8642/p/{profile}"
verification_key = f"syncode-production-verification-{uuid4().hex}"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json",
    "X-Hermes-Session-Key": verification_key,
}
request = Request(
    f"{base_url}/v1/runs",
    data=json.dumps(
        {
            "input": (
                "先用 skill_view 加载 syncode-training-plan Skill，"
                "再调用 get_my_learning_profile 工具读取当前学习档案，"
                "然后只用一句中文报告已做题数；不要猜测工具没有返回的数据。"
            )
        },
        ensure_ascii=False,
    ).encode("utf-8"),
    headers=headers,
    method="POST",
)
try:
    with urlopen(request, timeout=30) as response:
        created = json.loads(response.read(256_000))
except HTTPError as exc:
    detail = exc.read(256_000).decode("utf-8", errors="replace")
    raise RuntimeError(f"Hermes run creation failed with HTTP {exc.code}: {detail}") from exc
run_id = str(created.get("run_id") or "")
if not run_id:
    raise RuntimeError(f"Hermes did not return run_id: {created}")

events_request = Request(
    f"{base_url}/v1/runs/{run_id}/events",
    headers={key: value for key, value in headers.items() if key != "Content-Type"},
)
with urlopen(events_request, timeout=240) as response:
    events = response.read(2_000_000).decode("utf-8", errors="replace")
if "event: run.completed" not in events:
    raise RuntimeError(f"Hermes run did not complete; final stream tail: {events[-1200:]}")
if "get_my_learning_profile" not in events:
    raise RuntimeError("Hermes completed without the required SynCode MCP tool call")
if "skill_view" not in events or "syncode-training-plan" not in events:
    raise RuntimeError("Hermes completed without loading the required platform Skill")
print(f"[verify-hermes] live run completed: {run_id}")
PY
elif [[ "$VERIFY_HERMES_LIVE_RUN" != "false" ]]; then
  echo "VERIFY_HERMES_LIVE_RUN must be true or false" >&2
  exit 1
else
  echo "[verify-hermes] live run disabled explicitly"
fi

echo "[verify-hermes] production Hermes acceptance passed"
