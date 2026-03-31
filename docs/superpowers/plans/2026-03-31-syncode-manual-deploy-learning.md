# SynCode Manual Deploy Learning Plan

> For this learning track, keep `codex/live-20260331` as the archived live baseline and use `codex/learning-source-only` as the hands-on branch. The servers have already been reset to a clean Swarm-only state.

**Goal:** Rebuild the full path from stable source code to cloud deployment by hand, starting from middleware on Swarm and ending with GitHub-driven CI/CD.

**Baseline:** Source code remains intact, deployment assets have been stripped from the learning branch, and both cloud servers keep only Docker Engine plus the Swarm cluster itself.

**Tech Stack:** Docker Swarm, MySQL, Redis, RabbitMQ, Nacos, Spring Cloud Alibaba, Next.js, GHCR, GitHub Actions

---

## Current Baseline

- Live archive branch: `codex/live-20260331`
- Live archive tag: `v0.1.0-live-20260331`
- Learning branch: `codex/learning-source-only`
- Manager: `101.96.200.76`
- Worker: `101.96.200.77`
- Current server state: no business services, no middleware, no overlay networks except Swarm ingress, no persisted project data

## Lesson Order

### Lesson 0: Freeze the Baseline

**Status:** Completed

- Archive the current deployable state into a dedicated branch and tag.
- Create a separate learning branch that keeps source code but removes deployment assets.
- Reset the cloud servers to a clean Swarm-only state.

### Lesson 1: Rebuild Swarm Runtime Foundations

**Goal:** Understand the minimum infrastructure needed before any middleware is deployed.

- Inspect Swarm nodes and their roles.
- Add explicit node labels for future placement.
- Create project overlay networks by hand.
- Decide which services belong on manager vs worker.

### Lesson 2: Deploy Core Middleware by Hand

**Goal:** Bring up the stateful dependencies on Swarm without any GitHub Actions.

- Deploy MySQL with a persistent volume.
- Deploy Redis with a password and a persistent volume.
- Deploy RabbitMQ with management UI and persistent data.
- Deploy Nacos with a persistent volume.
- Verify each service from the server side before moving on.

### Lesson 3: Point Local Code to Cloud Middleware

**Goal:** Keep source code running locally while externalizing middleware to the cloud.

- Replace local middleware addresses with cloud addresses in local configuration.
- Import runtime configuration into server-side Nacos.
- Verify `gateway`, `friend`, and `system` can run locally against the cloud middleware.

### Lesson 4: Package One Service into a Docker Image

**Goal:** Learn how source code becomes a deployable artifact.

- Start with one service, preferably `app` or `gateway`.
- Write or restore its Dockerfile by hand.
- Build the image locally.
- Run the image locally and verify behavior.

### Lesson 5: Push Images to GHCR

**Goal:** Understand the role of an image registry between local builds and server deployment.

- Log in to GHCR.
- Tag images with a stable naming rule.
- Push them manually.
- Pull them back once to confirm the registry path is correct.

### Lesson 6: Deploy Services to Swarm

**Goal:** Replace local runtime with cloud runtime one layer at a time.

- Deploy one stateless service first.
- Learn `docker service create`, `docker service update`, and `docker service ps`.
- Move to `docker stack deploy` only after single-service deployment is understood.

### Lesson 7: Restore Full Stack Composition

**Goal:** Rebuild the production topology in ordered layers.

- `infra` layer first
- `runtime` layer second
- `edge` layer last
- Verify each layer before proceeding

### Lesson 8: Reintroduce GitHub Actions

**Goal:** Turn the manual path into an automated path after every step is understood.

- Add CI first: tests and builds
- Add image build and GHCR push second
- Add deploy workflow last
- Compare each workflow step with the manual command you already executed

## Rules for This Learning Track

- Do not skip directly to GitHub Actions before the equivalent manual step has been executed once.
- Do not deploy multiple unknown layers at the same time.
- Verify each lesson with concrete commands before proceeding.
- Keep the live archive branch untouched so there is always a known-good reference point.
