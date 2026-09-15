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

This avoids two unstable dependencies:

- GitHub-hosted runners SSHing into domestic production for every release.
- Production nodes pulling large images from foreign registries during rollout.

## Key Files

- [docker/java-service.Dockerfile](/D:/Project/OnlineOJ/bite-oj-master/bite-oj-master/deploy/prod/docker/java-service.Dockerfile)
- [docker/next-app.Dockerfile](/D:/Project/OnlineOJ/bite-oj-master/bite-oj-master/deploy/prod/docker/next-app.Dockerfile)
- [docker/oj-agent.Dockerfile](/D:/Project/OnlineOJ/bite-oj-master/bite-oj-master/deploy/prod/docker/oj-agent.Dockerfile)
- [swarm/stack.yml](/D:/Project/OnlineOJ/bite-oj-master/bite-oj-master/deploy/prod/swarm/stack.yml)
- [scripts/build-images.sh](/D:/Project/OnlineOJ/bite-oj-master/bite-oj-master/deploy/prod/scripts/build-images.sh)
- [scripts/sync-worker-images.sh](/D:/Project/OnlineOJ/bite-oj-master/bite-oj-master/deploy/prod/scripts/sync-worker-images.sh)
- [scripts/deploy.sh](/D:/Project/OnlineOJ/bite-oj-master/bite-oj-master/deploy/prod/scripts/deploy.sh)
- [env/stack.env.prod.template](/D:/Project/OnlineOJ/bite-oj-master/bite-oj-master/deploy/prod/env/stack.env.prod.template)
- [env/runtime.env.prod.template](/D:/Project/OnlineOJ/bite-oj-master/bite-oj-master/deploy/prod/env/runtime.env.prod.template)
- [env/github-secrets-guide.md](/D:/Project/OnlineOJ/bite-oj-master/bite-oj-master/deploy/prod/env/github-secrets-guide.md)

## Release Flow

1. GitHub runs `ci.yml`.
2. After `ci.yml` succeeds on `main`, `cd-test.yml` deploys and smoke-tests the test environment.
3. GitHub sends the production approval notification; an administrator manually starts `cd.yml` with the successful CI run id.
4. The self-hosted runner on `101.96.200.76` downloads that exact tested revision.
5. The job migrates and validates the production database, then renders the runtime configuration.
6. The manager builds the production images locally.
7. The manager saves and copies the worker image set to `101.96.200.77`, then verifies those images exist on the worker.
8. The manager runs `docker stack deploy --resolve-image never`.

## First-Time Bootstrap

1. Fill in the required GitHub Secrets described in [env/github-secrets-guide.md](/D:/Project/OnlineOJ/bite-oj-master/bite-oj-master/deploy/prod/env/github-secrets-guide.md).
2. Generate a fresh runner registration token for this repository.
3. Save that token as `SELF_HOSTED_RUNNER_BOOTSTRAP_TOKEN`.
4. Run `bootstrap-runner.yml`.
5. Confirm a runner with label `syncode-prod` is online.
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

## Notes

- This pipeline assumes the worker services remain constrained to the worker node.
- If you move more services to the worker, update `WORKER_IMAGE_LIST` in the stack env secret/template.
- `oj-judge` now expects the worker to provide `/var/run/docker.sock`, `/app/user-code`, and `/app/user-code-pool` as bind-mountable host paths.
- If you later add a domestic registry, the image sync step can be replaced with local push/pull logic.
