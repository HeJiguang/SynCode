# SynCode Swarm Deployment

This directory contains the first Swarm-oriented deployment skeleton for SynCode.

## 1. Stack layout

- `deploy/swarm/stacks/infra.yml`
  - stateful dependencies
- `deploy/swarm/stacks/runtime.yml`
  - Java services and `oj-agent`
- `deploy/swarm/stacks/edge.yml`
  - `web`, `app`, and `admin`

## 2. Node labels

Apply labels before deployment:

```powershell
docker node update --label-add syncode.role=edge <edge-node-name>
docker node update --label-add syncode.role=runtime <runtime-node-name>
```

Recommended mapping:

- `4c4u` -> `syncode.role=edge`
- `4c8u` -> `syncode.role=runtime`

## 3. Shared overlay networks

Create shared overlay networks once on the Swarm manager:

```powershell
docker network create --driver overlay --attachable syncode-public
docker network create --driver overlay --attachable syncode-app
docker network create --driver overlay --attachable syncode-data
```

## 4. Deploy order

Deploy in this order:

```powershell
docker stack deploy -c deploy/swarm/stacks/infra.yml syncode-infra
docker stack deploy -c deploy/swarm/stacks/runtime.yml syncode-runtime
docker stack deploy -c deploy/swarm/stacks/edge.yml syncode-edge
```

Swarm does not honor local Compose-style dependency waiting, so do not deploy `runtime` before `infra` is healthy.

## 5. Current scope

Current scope for this rollout:

- finish Swarm deployment assets
- finish GitHub CI/CD assets
- perform real server-side deployment

Deferred for a later phase:

- `runtime-control`
- manual cold-start launch panel
- idle shutdown

## 6. Environment variables

The stack files use these important variables:

- `IMAGE_TAG`
- `MYSQL_ROOT_PASSWORD`
- `MYSQL_APP_PASSWORD`
- `REDIS_PASSWORD`
- `RABBITMQ_DEFAULT_USER`
- `RABBITMQ_DEFAULT_PASS`
- `JWT_SECRET`
- `MAIL_USERNAME`
- `MAIL_PASSWORD`
- `LLM_API_KEY`
- `SYNCODE_RUNTIME_REPLICAS`

Set them in the manager shell before running `docker stack deploy`, or provide them through your deployment workflow.

## 7. Current image naming convention

The stack skeleton expects these GHCR images:

- `ghcr.io/hejiguang/syncode-web`
- `ghcr.io/hejiguang/syncode-app`
- `ghcr.io/hejiguang/syncode-admin`
- `ghcr.io/hejiguang/syncode-gateway`
- `ghcr.io/hejiguang/syncode-friend`
- `ghcr.io/hejiguang/syncode-system`
- `ghcr.io/hejiguang/syncode-job`
- `ghcr.io/hejiguang/syncode-judge`
- `ghcr.io/hejiguang/syncode-oj-agent`

## 8. Next implementation steps

This deployment skeleton intentionally does not yet claim full cold-start completion.

Remaining required work for the later cold-start phase:

- add `runtime-control`
- add `/app` launch-aware public entry
- add heartbeat and 30-minute idle shutdown
- validate Nacos registration behavior inside Swarm
- validate `oj-judge` Docker runtime on the target node
