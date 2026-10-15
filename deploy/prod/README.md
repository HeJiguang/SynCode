# OnlineOJ Production Deploy

This directory contains the production deploy assets for the domestic-first release pipeline.

## Deployment Model

- `ci.yml` runs Java, Python, frontend, and MySQL migration checks on GitHub-hosted runners.
- `cd-test.yml` automatically deploys a successful `main` build to the isolated test environment.
- `bootstrap-runner.yml` installs a self-hosted runner on `101.96.200.76`.
- `cd.yml` runs on that self-hosted runner.
- The manager builds all production images locally.
- The manager copies worker-only images to `101.96.200.77`.
- The manager runs `docker stack deploy` after both nodes have the required images.
- `docker stack deploy` uses `--resolve-image never`, so Swarm does not try to resolve tags against an external registry during rollout.
- Nginx Swarm configs use a content digest in their resource names so immutable configs can be updated safely.
- The deploy command waits for every service update and desired replica to converge before smoke or end-to-end tests start.

This avoids two unstable dependencies:

- GitHub-hosted runners SSHing into domestic production for every release.
- Production nodes pulling large images from foreign registries during rollout.

Two application layouts are supported from the same module sources:

- `swarm/stack.yml` keeps gateway, system, friend, job, and judge as separate JVMs.
- `swarm/stack-compact.yml` runs system, friend, and trusted-exam jobs in `oj-runtime`; judge remains a separate JVM and the Python agent remains a separate process.

Both layouts run Hermes as the workspace AI agent core. `oj-agent-tools` exposes the authenticated,
user-scoped OJ MCP tools, the internal learning-memory prefetch endpoint and profile provision endpoint. `oj-agent` only serves training-plan requests from
the Java training flow. Hermes and `oj-agent-tools` must remain on the same manager node because they share
the local `hermes_data` profile volume and `hermes_platform_skills` catalog volume.

The compact layout is the default for the 4 vCPU / 8 GiB test host. It preserves the public `/system/**` and `/friend/**` contracts, performs gateway-equivalent JWT validation in a Servlet filter, and keeps the judge sandbox outside the business JVM.

## Key Files

- `docker/java-service.Dockerfile`
- `docker/next-app.Dockerfile`
- `docker/oj-agent.Dockerfile`
- `docker/hermes.Dockerfile`
- `swarm/stack.yml`
- `swarm/stack-compact.yml`
- `../test/swarm/infra.yml`
- `scripts/build-images.sh`
- `scripts/sync-worker-images.sh`
- `scripts/deploy.sh`
- `env/stack.env.prod.template`
- `env/runtime.env.prod.template`
- `env/github-secrets-guide.md`

## Release Flow

1. GitHub runs `ci.yml`.
2. After `ci.yml` succeeds on `main`, `cd-test.yml` deploys and smoke-tests the test environment.
3. GitHub sends the production approval notification; an administrator manually starts `cd.yml` with the successful CI run id.
4. The self-hosted runner on `101.96.200.76` downloads that exact tested revision.
5. The job migrates and validates the production database, then renders the runtime configuration.
6. The manager builds the production images locally.
7. The manager saves and copies the worker image set to `101.96.200.77`, then verifies those images exist on the worker.
8. The manager runs `docker stack deploy --resolve-image never` and waits for the Swarm rollout to converge.
9. The deploy script validates the Hermes profile policy, memory provider, platform catalog, Elasticsearch,
   read-only mount and one real Hermes/MCP/SSE turn.

Before the first Hermes rollout, generate independent values for `SYNCODE_HERMES_API_KEY`,
`SYNCODE_HERMES_SESSION_SECRET`, `SYNCODE_HERMES_PROVISION_KEY`, and `SYNCODE_MCP_SERVICE_KEY`, then configure
`HERMES_DEEPSEEK_API_KEY`. Preserve `hermes_data` across deploys and rollbacks because it is the source of
truth for Hermes profiles, sessions and native memory. Preserve `hermes_platform_skills` because it contains
administrator-approved shared Skill releases. See `docs/architecture/hermes-agent-runtime.md` for the full
boundary and smoke-test order.

Skill governance also requires a reachable Elasticsearch service and dense multilingual embeddings. The Agent
image includes the 512-dimensional `BAAI/bge-small-zh-v1.5` model and uses it through
`SYNCODE_SKILL_EMBEDDING_URL=local://fastembed` by default. An OpenAI-compatible endpoint can override the local
model through `SYNCODE_SKILL_EMBEDDING_URL`, `SYNCODE_SKILL_EMBEDDING_API_KEY`,
`SYNCODE_SKILL_EMBEDDING_MODEL`, and `SYNCODE_SKILL_EMBEDDING_DIMENSIONS`. The platform catalog is stored in the separate
`hermes_platform_skills` volume. `oj-agent-tools` owns the writable mount; Hermes receives the same volume
read-only at `/opt/platform-data/platform-skills`.

CI pins, verifies, and stages the local model in the tested deployment bundle. The Agent image loads that directory
with FastEmbed's offline mode, so image builds and runtime inference never depend on Hugging Face availability.
For a manual source checkout build, run `deploy/prod/scripts/fetch-fastembed-model.sh` before `build-images.sh`.

The same embedding provider powers user-scoped layered learning-memory recall through the separate
`SYNCODE_LEARNING_MEMORY_INDEX`. When embeddings are unavailable, learning-memory tools continue with
database retrieval and report the fallback mode explicitly.

## First-Time Bootstrap

1. Fill in the required GitHub Secrets described in `env/github-secrets-guide.md`.
2. Generate a fresh runner registration token for this repository.
3. Save that token as `SELF_HOSTED_RUNNER_BOOTSTRAP_TOKEN`.
4. Run `bootstrap-runner.yml`; for test use labels `syncode-test,onlineoj-test`, otherwise keep the production defaults.
5. Confirm a runner with the selected environment label is online.
6. Trigger `cd.yml` manually once.

## Manual Local Deploy

```bash
BUILD_LOCAL_IMAGES=true \
SYNC_WORKER_IMAGES=true \
WORKER_SSH_KEY_FILE=/path/to/worker_id_ed25519 \
STACK_ENV_FILE=deploy/prod/env/stack.env \
RUNTIME_ENV_FILE=deploy/prod/env/runtime.env \
deploy/prod/scripts/deploy.sh
```

For compact deployment, set `DEPLOYMENT_MODE=compact`, `RUNTIME_IMAGE`, and `BACKEND_NETWORK`, then use `STACK_FILE=deploy/prod/swarm/stack-compact.yml`. The external backend overlay network must exist before deploying the infrastructure and application stacks.

`STACK_WAIT_TIMEOUT_SECONDS` controls the rollout timeout (default `600`), and `STACK_WAIT_POLL_SECONDS` controls its polling interval (default `5`). A paused, rolling-back, or timed-out service update fails the deployment before acceptance tests begin.

Hermes acceptance is enabled by default. `VERIFY_HERMES_PRODUCTION=false` skips all Hermes post-deploy checks,
and `VERIFY_HERMES_LIVE_RUN=false` skips only the paid model turn. These switches are intended for diagnosed
recovery work; a normal test or production release must leave both checks enabled.

## Production Login Email

The official production deploy and recovery workflows reuse the configured
`DEPLOY_NOTIFY_SMTP_*` GitHub secrets for user login verification emails. They
run `scripts/configure-login-mail.sh`, enable real delivery, and stop before
deployment if the SMTP host, port, username, or authorization code is missing.

QQ Mail normally uses port `465` with implicit TLS. Port `587` and other SMTP
submission ports use STARTTLS. Use an SMTP authorization code rather than the
mailbox login password. After each initial setup or credential rotation, request
a verification code from the production login page and confirm delivery.

## Notes

- This pipeline assumes the worker services remain constrained to the worker node.
- If you move more services to the worker, update `WORKER_IMAGE_LIST` in the stack env secret/template.
- `oj-judge` now expects the worker to provide `/var/run/docker.sock`, `/app/user-code`, and `/app/user-code-pool` as bind-mountable host paths.
- Java business services use distinct logical-clock Snowflake worker IDs and named volumes for ID high-watermark state. Preserve those volumes during rollback or host migration; see `docs/architecture/logical-clock-snowflake.md`.
- If you later add a domestic registry, the image sync step can be replaced with local push/pull logic.
