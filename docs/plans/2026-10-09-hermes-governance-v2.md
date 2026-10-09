# Hermes Governance V2

Date: 2026-10-09

## Goal

Keep Hermes as the only Agent core while giving SynCode a stable, user-facing governance layer for memory,
run recovery and tenant isolation. SynCode may authenticate, route and display Hermes state, but it must not
reimplement the Agent loop, memory policy, context compression or tool execution.

```text
Browser -> Next.js BFF -> Runtime Gateway -> selected Agent Runtime
                                      \-> Hermes -> approved SynCode MCP tools
```

## Ownership

Hermes owns the Agent loop, model calls, context compression, memory proposals, memory writes, skills, tool
selection/execution and streamed Agent events. The Runtime Gateway owns trusted identity injection, stable
public IDs, Runtime selection and protocol translation. The browser only displays state and records an
authenticated user's review decision. MCP tools enforce OJ data permissions using server-derived identity.

The browser and model must never supply `userId`, a Hermes profile name, upstream credentials or authorization
scope. Shell, filesystem, browser, Docker and general code-execution tools remain unavailable to Hermes.

## Phase 2A: Memory governance and recoverable runs

- [x] Confirm the ownership boundary and inspect Hermes' native compression, memory gate and run APIs.
- [x] Enable Hermes' native `memory.write_approval` for every SynCode user profile, including existing profiles.
- [x] Add a narrow Hermes API extension that reads native memory and calls native pending/approve/reject logic.
- [x] Expose Runtime-neutral memory APIs and Runtime-pinned memory-candidate IDs.
- [x] Expose `GET /v1/runs/{runId}` and pass SSE replay cursors through all proxy layers.
- [x] Add a memory-review drawer to the learning assistant.
- [x] Split control, Runtime and OJ data traffic across explicit overlay networks.
- [x] Add backend, frontend and image-patch contract tests.
- [x] Run focused test suites and update this document with the result.

### Stable Runtime API

```text
GET  /v1/memories
GET  /v1/memory-candidates
POST /v1/memory-candidates/{candidateId}/approve
POST /v1/memory-candidates/{candidateId}/reject
GET  /v1/runs/{runId}
GET  /v1/runs/{runId}/events?last_seq=N
```

`memory_candidate` public IDs use the `rtm.<runtime>.<native-id>` form. This pins a pending decision to the
Runtime that created it, so a hot switch cannot approve the wrong Runtime's data.

### Acceptance criteria

1. A Hermes memory write is staged and never committed before user approval.
2. A signed-in user can inspect `MEMORY.md`, `USER.md` and the exact proposed operation.
3. Approve applies the proposal through Hermes' own `apply_memory_pending`; reject discards it through Hermes'
   own pending store.
4. Candidate IDs reject traversal and malformed native IDs.
5. Existing sessions, runs and memory candidates remain routed to their owning Runtime after activation changes.
6. Reconnecting with `Last-Event-ID` or `last_seq` reaches Hermes unchanged, and SSE `id:` fields survive proxying.
7. Hermes still receives only the `memory` and `syncode` toolsets; the MCP layer still derives user identity.

## Phase 2B: Context review before compression

- [x] Add the `syncode_reviewed` Hermes Context Engine instead of implementing compression in SynCode.
- [x] Generate the draft through Hermes' native `ContextCompressor` at the configured token threshold.
- [x] Persist source/retained message IDs, redacted excerpts, token counts, a source hash and SessionDB watermark.
- [x] Pause through Hermes' native approval queue and expose Runtime-neutral list/approve/edit/reject endpoints.
- [x] Reject approval if the SessionDB watermark changed while the user was reviewing the draft.
- [x] Preserve the original Chat transcript and restore all compressor state on rejection or stale review.
- [x] Display the source context and editable summary in the existing governance drawer.

Context reviews use `rtc.<runtime>.<native-id>` public IDs. The native Run reports
`waiting_for_approval`; `review_kind=context_summary` gives the UI the more specific
`WAITING_FOR_CONTEXT_REVIEW` state without creating a second approval system.

## Phase 2C: Durable multi-user Runtime foundation

- [x] Keep Chat and complete transcripts in each user's Hermes SessionDB profile.
- [x] Persist Runtime-neutral Run, rewritten Event and projected Artifact records in a SQLite WAL ledger.
- [x] Replay stored SSE events and return stored Run/Artifact data when the owning Runtime is unavailable.
- [x] Enforce Run ownership at the gateway and derive user identity from the authenticated BFF request.
- [x] Reserve per-user and per-Runtime concurrency slots atomically and interrupt stale reservations/Runs.
- [x] Let only typed `run.*` events change durable Run state or release concurrency admission.
- [x] Automatically fail over only new sessions and sessionless Runs; never migrate a pinned session silently.
- [x] Keep Hermes off the backend network and expose only `memory` plus the controlled `syncode` MCP toolset.

The ledger is a single-node SQLite store on the manager-pinned `runtime_gateway_data` volume. Moving the Runtime
Gateway to active-active replicas would require a transactional shared admission/event store first.

## Phase 2D: OJ recommendation execution loop

- [x] Expose profile, submission, question search, current-plan and effect queries as user-scoped read tools.
- [x] Add controlled writes for saving plans, updating owned tasks and recording recommendation feedback.
- [x] Mark write tools non-read-only so Hermes' untrusted MCP policy invokes native user approval.
- [x] Validate real enabled questions and prevent cross-user task changes; never accept `userId` as a tool argument.
- [x] Persist recommendation events and compute attempts/passes only from submissions after plan creation.
- [x] Update the training Skill to show a plan before saving and use measured effects during review.

## Phase 2E: Scheduled, reviewed learning profile

- [x] Add a server-side scheduler that scans learning-data watermarks without handling model prompts or results.
- [x] Add an authenticated Gateway trigger that binds user identity and starts a normal Hermes Runtime Run.
- [x] Deduplicate unchanged data, release failed claims and serialize refresh Runs per user.
- [x] Add `get_my_recent_submissions` as a read-only, user-scoped MCP tool without raw source code.
- [x] Add the `syncode-learning-profile` Skill and require the native `memory(target=user)` approval path.
- [x] Deploy the scheduler in both microservice and compact Swarm layouts.

## Remaining follow-up

- Build and roll out the tested revision on the Docker-capable production runner, then execute the production
  acceptance checks. This item is complete only after the deployed stack and user review path are verified.

## Progress log

- 2026-10-09: Created the V2 plan after inspecting the current Runtime Gateway and Hermes upstream at
  `1744a19e0df568c647e4f3ff9c37f2a284a282fb`.
- 2026-10-09: Implemented native memory review, Runtime-pinned candidate IDs, Run status/SSE replay pass-through,
  the review UI, profile migration and network separation.
- 2026-10-09: Verification passed: 108 Python tests, the complete app test command, the Next.js production
  build, both Hermes patch compatibility scripts, and a patch/compile check against Hermes upstream
  `1744a19e0df568c647e4f3ff9c37f2a284a282fb`. Visual QA passed at 1440x900 and 390x844 with no horizontal
  overflow. Docker is not installed on this workstation, so the actual `HERMES_IMAGE` build remains a CI/deploy
  validation rather than a local validation.
- 2026-10-09: Added the reviewed Hermes Context Engine, durable Run/Event/Artifact ledger, ownership and
  concurrency admission, new-resource failover, controlled OJ write tools, recommendation telemetry/effect
  queries, Runtime/BFF context-review APIs and the editable review UI. Added focused restart, isolation,
  failover, review-staleness, database-write and tool-annotation tests.
- 2026-10-09: Hardened rejected context-review rollback and Run event status projection. Final verification
  passed: 122 Python tests, the complete app test command, the Next.js production build, all three Hermes
  compatibility scripts, Shell syntax checks, both Swarm YAML parses and `git diff --check`. The context-review
  drawer was exercised against local mock Runtime data at desktop size with no visible overflow or overlap.
  Docker remains unavailable on this workstation, so image build and server rollout are still pending.
- 2026-10-09: Added scheduled learning-profile refreshes. A dedicated scheduler sends only trusted user/source
  watermarks to the Runtime Gateway; Hermes reads scoped learning tools and stages a `USER.md` proposal through
  native memory approval. Unchanged watermarks are deduplicated and newer snapshots cannot overlap an active
  refresh for the same user.
