# Agent Runtime Gateway and Hermes Adapter

Hermes is SynCode's initial agent core. It is not an LLM gateway hidden behind `oj-agent`, and SynCode no
longer depends on Hermes-specific HTTP paths. A small anti-corruption layer exposes the stable SynCode Agent
Runtime protocol and adapts it to Hermes.

```text
Browser
  -> authenticated Next.js Runtime proxy (`/api/ai/runtime/*`)
     -> Agent Runtime Gateway (`/v1/*`)
        -> active adapter for new sessions
           -> Hermes profile syncode-u<userId>
              -> Hermes sessions, reviewed memory, skills, agent loop, approvals and streaming
              -> SynCode HTTP MCP tools
                 -> user-scoped OJ reads and approved training writes
              -> DeepSeek
```

The workspace chat does not ask `oj-agent` to build prompts, parse model-produced tool JSON, execute a
second agent loop, poll Hermes, or fall back to a direct DeepSeek client. The Runtime gateway only authenticates,
routes, translates IDs and streams bytes/events. The old `oj-agent` and `/api/ai/hermes/*` code remains during
migration, but production no longer injects native Hermes credentials into `app` or connects it to the Hermes
network. Re-enabling that legacy path is an explicit rollback configuration change, not a silent fallback.

## Ownership boundary

Hermes owns:

- the agent loop and model calls;
- sessions, transcript persistence, context compression and long-term memory;
- skill and workflow selection;
- MCP tool discovery, selection and execution;
- approval state, stop and mid-run steer;
- token streaming and structured run events;
- provider failures and agent-level diagnostics.

SynCode owns:

- login, browser sessions and resolving the authenticated SynCode `userId`;
- the OJ UI and factual workspace state such as the question, editor contents and latest judge result;
- OJ domain data and narrowly scoped MCP implementations;
- a stable Runtime protocol for sessions, runs, event streams, artifacts and run control;
- public ID ownership, the Runtime registry and atomic active-Runtime selection;
- durable Run/Event/Artifact projections, concurrency admission and new-resource failover;
- a transparent HTTP/SSE routing boundary so a concrete Runtime is never exposed publicly.

The Hermes adapter, not the UI or Next.js, owns the Hermes-specific profile name, provision request,
`X-Hermes-Session-Key`, bearer credential and native endpoint paths. The gateway does not own memory, tools,
prompts, agent decisions or a second execution loop.

## Request flow

1. Next.js resolves the current user through `/friend/user/detail`.
2. Next.js passes only the trusted numeric user ID and a derived session key to the private Runtime gateway.
3. The gateway chooses the active Runtime only when a new session is created. The selected adapter maps the
   user to `syncode-u<userId>` and provisions the profile when needed.
4. The gateway returns a public ID such as `rts.hermes.<base64url-native-id>`. That ID permanently records the
   owning Runtime without moving the native session or memory into SynCode.
5. A user action sends a generic workflow such as `progressive-hint` plus factual workspace `instructions`.
   The Hermes adapter translates the workflow to a native Skill command such as `/syncode-tutor`; the UI does
   not know that syntax.
6. Next.js calls the stable `/v1/runs` protocol. The gateway decodes the session owner, invokes the matching
   adapter and returns a pinned run ID such as `rtr.hermes.<base64url-native-id>`.
7. Hermes may call the SynCode MCP server itself. SynCode does not interpret a model response and then call
   the tool on Hermes' behalf.
8. The gateway rewrites only `run_id` and `session_id` in SSE JSON payloads. Tokens, tool progress, approvals
   and terminal status otherwise reach the UI with their native semantics intact.

Approvals, steer and stop are passed through to the matching native run endpoints. The unused session
`chat/stream` proxy is deliberately not exposed.

Run status is available through `GET /v1/runs/{runId}`. Every rewritten SSE frame is durably appended to the
Runtime ledger before it is sent to the browser. Reconnects replay the ledger first and then continue from the
owning Runtime using `Last-Event-ID`/`last_seq`; terminal Runs never reconnect upstream after their terminal
event has been stored. `GET /v1/runs/{runId}/artifacts` exposes explicit Runtime artifacts and terminal workflow
outputs projected from the Event stream. Only typed `run.*` events can change the durable Run status; a tool or
subagent payload that happens to contain `status=completed` cannot release the Run's concurrency slot early.

## User isolation

There is one named Hermes profile per SynCode user:

```text
/opt/data/profiles/syncode-u42
```

The Hermes adapter derives the name from the trusted numeric user ID. There is no shared-profile fallback.
Every Hermes request uses `/p/syncode-u42/...` and a server-generated `X-Hermes-Session-Key`; the browser
cannot provide or override the user, profile or upstream credentials.

Hermes adds `X-SynCode-Hermes-Profile: syncode-u42` to every SynCode MCP request through its native
`identity_header` support. The MCP service validates the exact profile format and derives `userId=42`; tool
arguments never contain a model-selected user ID. A separate bearer key authenticates Hermes as the MCP
caller.

The named volume is mounted at `/opt/data` in Hermes and `/var/lib/hermes` in the profile provisioner. Both
containers use UID/GID 10000 and are constrained to the manager node so the local Swarm volume cannot split
across hosts.

## Skills and tools

Teaching behavior lives in versioned Hermes skills:

- `syncode-tutor`: progressive hints and explanation;
- `syncode-diagnosis`: evidence-based code and judge-result diagnosis;
- `syncode-training-plan`: a short plan based on the user's learning data;
- `syncode-learning-profile`: a scheduled synthesis of stable learning evidence into a reviewed `USER.md`
  proposal.

The profile enables only Hermes' native memory toolset and the `syncode` MCP toolset on the API-server
surface. Broad host capabilities such as shell, files, browser, Docker and code execution are not enabled.

Every provisioned profile explicitly enables both built-in memory targets and `memory.write_approval`. The
provisioner also atomically reconciles existing profile configs, so this policy applies to users created before
the feature was deployed. In the API-server environment Hermes stages writes under its own profile home rather
than changing `MEMORY.md` or `USER.md` immediately.

SynCode adds a narrow API module to the Hermes image. It does not implement memory semantics. It reads memory
through Hermes' `load_on_disk_store`, lists candidates through `write_approval.list_pending`, applies approved
changes through `apply_memory_pending`, and removes approved/rejected records through `discard_pending`.
Candidate IDs must be exactly eight lowercase hexadecimal characters before any pending path is accessed.

The stable Runtime protocol exposes:

```text
GET  /v1/memories
GET  /v1/memory-candidates
POST /v1/memory-candidates/{candidateId}/approve
POST /v1/memory-candidates/{candidateId}/reject
```

The gateway encodes native candidates as `rtm.<runtime>.<base64url-native-id>`. It aggregates visible memory
and pending candidates from registered Runtimes, but every review action is permanently routed to the Runtime
encoded in the candidate ID. The browser sends neither `userId` nor a profile name.

The SynCode MCP service exposes these read-only tools:

- `get_question`
- `get_my_submission_history`
- `get_my_recent_submissions`
- `get_my_learning_profile`
- `get_my_current_training_plan`
- `search_practice_questions`
- `get_my_training_effects`

It also exposes controlled writes:

- `save_my_training_plan`
- `update_my_training_task`
- `record_my_recommendation_feedback`

Read tools carry `readOnlyHint=true`; write tools explicitly carry `readOnlyHint=false`. The server is configured
as `trust: untrusted`, so Hermes routes writes through its native approval flow. The tool schema contains no
`userId`; the MCP service derives it from the server-injected profile header and scopes every query/update.

The training-plan Skill reads the profile, submissions and current plan, searches real enabled questions, shows
the proposal to the learner, and saves only after explicit acceptance. Plan/task/feedback writes create a
recommendation event timeline. Later reviews use only submissions made after the plan was created to report
attempts, best score, passes, completed tasks and skipped tasks.

## Scheduled learning profile

`learning-profile-scheduler` periodically reads only a server-side list of `(user_id, source_watermark)` values.
The watermark combines the newest submission, submission count and latest judge/update time, so a new result can
trigger a refresh without sending submission content through the scheduler. It calls the authenticated internal
endpoint:

```text
POST /internal/learning-profile-refreshes
```

The Runtime Gateway binds the trusted user to a dedicated background session key, atomically compares the
watermark in `learning_profile_refreshes`, and starts a normal `learning-profile` Runtime Run. The Hermes adapter
maps that workflow to `/syncode-learning-profile`. The scheduler never calls a model, builds the profile, supplies
tool arguments or writes memory.

Hermes then reads the current profile, recent cross-question submissions, active plan and measured effects through
the same user-scoped MCP tools available to interactive sessions. It condenses stable evidence and invokes its
native `memory` tool with `target=user`. Because every profile has `memory.write_approval=true`, the operation is
stored as a pending candidate and `USER.md` remains unchanged until the user approves it in the governance drawer.

The gateway serializes refreshes per user. An unchanged watermark is a no-op, a failed trigger releases its claim
for retry, and a newer watermark waits while the previous profile Run is active. Runtime and candidate IDs remain
pinned, so a hot switch cannot move a pending profile decision to another Runtime. The scheduler starts at most
five new profile Runs per sweep by default, preserving Runtime capacity for interactive learning requests.

## Context budget and review

Every provisioned profile selects Hermes' `syncode_reviewed` Context Engine. It subclasses Hermes'
`ContextCompressor`, so the Runtime itself decides when the token threshold is reached and uses its configured
model to generate the summary. Before that summary replaces active context, the engine writes a candidate under
the user's Hermes profile and blocks on Hermes' native approval queue.

The candidate contains redacted source excerpts, source/retained message IDs, token counts, a source hash and the
SessionDB message watermark. The user can edit and approve the summary or reject compression. Approval is
discarded as stale when the watermark changed during review. Rejection restores the original active context and
the compressor's pre-generation cooldown, failure and overload state, so the review gate is a true pre-commit
boundary. The complete original transcript remains in Hermes SessionDB in every case.

Stable endpoints are:

```text
GET  /v1/context-candidates
POST /v1/context-candidates/{candidateId}/approve
POST /v1/context-candidates/{candidateId}/reject
```

Candidate IDs are Runtime-pinned as `rtc.<runtime>.<native-id>`.

## Durable isolation and admission

Chats and full transcripts remain native Hermes SessionDB data inside the user's profile. The Runtime Gateway
adds a durable protocol ledger with `runtime_runs`, `runtime_events`, `runtime_artifacts` and
`runtime_admissions`. The ledger is stored in SQLite WAL mode on `runtime_gateway_data`; all reads and control
actions check the authenticated user against the stored Run owner.

Admission uses one immediate transaction to count active Runs plus in-progress reservations. Defaults are two
concurrent Runs per user and twenty per Runtime. Old active Runs are marked `interrupted` after the configured
stale window so crashed work cannot consume a slot forever.

## Services and configuration

Production adds four services alongside the compatibility `oj-agent` service:

- `hermes`: the official Hermes image extended with SynCode skills and the narrow memory-governance HTTP
  adapter; runs `gateway run`, multiplexes named profiles and keeps all Hermes state in `hermes_data`;
- `oj-agent-tools`: the existing Python image started with `app.mcp_gateway.server:app` on port 8016; serves
  MCP and the authenticated profile provision endpoint;
- `agent-runtime-gateway`: the Python image started with `app.runtime_gateway.server:app` on port 8017;
  exposes the stable Runtime protocol and keeps its registry plus durable ledger in `runtime_gateway_data`;
- `learning-profile-scheduler`: the Python image started with `app.profile_scheduler.server:app` on port 8018;
  scans learning-data watermarks and invokes only the authenticated internal refresh endpoint.

Stack-level secrets and settings:

```bash
HERMES_IMAGE=syncode-hermes:sha-...
HERMES_BASE_IMAGE=nousresearch/hermes-agent:latest
HERMES_MODEL=deepseek-chat
HERMES_DEEPSEEK_API_KEY=...
SYNCODE_HERMES_API_KEY=...
SYNCODE_HERMES_SESSION_SECRET=...
SYNCODE_HERMES_PROVISION_KEY=...
SYNCODE_AGENT_RUNTIME_GATEWAY_KEY=...
SYNCODE_MCP_SERVICE_KEY=...
```

Use independent random values for the five SynCode secrets. `SYNCODE_HERMES_API_KEY` is the private Hermes
API bearer key, not the DeepSeek key. No Hermes port is published through Swarm ingress or nginx.

The stack injects these internal addresses into Next.js, the gateway and the provisioner:

```text
SYNCODE_AGENT_RUNTIME_BASE_URL=http://agent-runtime-gateway:8017
SYNCODE_AGENT_RUNTIME_API_KEY=<SYNCODE_AGENT_RUNTIME_GATEWAY_KEY>
SYNCODE_AGENT_RUNTIME_SESSION_SECRET=<session-scope-secret>
SYNCODE_RUNTIME_LEDGER_PATH=/var/lib/syncode-runtime/runtime-ledger.sqlite3
SYNCODE_RUNTIME_MAX_RUNS_PER_USER=2
SYNCODE_RUNTIME_MAX_RUNS_PER_RUNTIME=20
SYNCODE_RUNTIME_RUN_STALE_SECONDS=3600
SYNCODE_RUNTIME_AUTO_FAILOVER=true
SYNCODE_LEARNING_PROFILE_POLL_SECONDS=900
SYNCODE_LEARNING_PROFILE_BATCH_SIZE=500
SYNCODE_LEARNING_PROFILE_MAX_RUNS_PER_SWEEP=5
SYNCODE_RUNTIME_DEFAULT_ADAPTER=hermes
SYNCODE_RUNTIME_DEFAULT_BASE_URL=http://hermes:8642
SYNCODE_RUNTIME_DEFAULT_PROVISION_URL=http://oj-agent-tools:8016/internal/profiles/ensure
SYNCODE_MCP_PUBLIC_URL=http://oj-agent-tools:8016/mcp
```

Hermes runs with `API_SERVER_HOST=0.0.0.0`, `API_SERVER_PORT=8642`, and
`GATEWAY_MULTIPLEX_PROFILES=true`. The official image entrypoint remains intact because it initializes s6,
repairs volume ownership and reconciles profiles.

Agent traffic uses separate overlay networks:

```text
app <-> agent-control <-> agent-runtime-gateway <-> learning-profile-scheduler
agent-runtime-gateway <-> agent-runtime <-> hermes
                                      \-> oj-agent-tools <-> backend <-> OJ services
learning-profile-scheduler <-> backend
```

Hermes is not attached to `backend`; it cannot resolve or directly connect to the OJ service names or database
containers. It reaches OJ data only through the approved MCP service. `app` is not attached to `agent-runtime`,
so Hermes credentials and native endpoints remain behind the Runtime Gateway.

## Hot switching

The internal control plane and stable Runtime API are authenticated with the dedicated
`SYNCODE_RUNTIME_GATEWAY_KEY` value sourced from `SYNCODE_AGENT_RUNTIME_GATEWAY_KEY`:

```text
GET  /internal/runtimes
PUT  /internal/runtimes/{name}
POST /internal/runtimes/{name}/activate
```

Registrations are immutable by name. To replace Hermes, register a new name such as `hermes-v2`, then call
`activate`. Activation health-checks the candidate first and atomically changes the active name only after a
successful check. A failed check leaves the current active Runtime unchanged.

Switching affects only sessions created after activation. Existing session IDs, in-flight run IDs, SSE
connections, approval decisions, steer requests and stop requests continue to route to their encoded owner.
Session history is aggregated from all registered Runtimes so old conversations remain visible. Unhealthy
inactive Runtimes produce a warning; an unhealthy active Runtime fails visibly.

Registry state is atomically written with file mode `0600` to
`/var/lib/syncode-runtime/registry.json`. Do not delete a registration that owns retained sessions. Supporting
a different Runtime implementation does not require changes in the browser, Next.js routes or UI. A Runtime
that already implements this protocol can use the built-in `syncode-v1` adapter and hot-plug through control
plane configuration alone. A Runtime with a different native API needs one server-side adapter like Hermes.

If the active Runtime fails while creating a new session or a sessionless Run, the gateway may choose another
registered healthy Runtime and returns `degraded_from` metadata. A request carrying an existing session ID never
fails over: it remains pinned to its owner, and the gateway serves any already stored Run/Event/Artifact state
while that Runtime is unavailable.

## Rollout order

1. Generate the five SynCode secrets and a DeepSeek key; update both stack and runtime environment files.
2. Build `AGENT_IMAGE` and `HERMES_IMAGE`.
3. Deploy the stack without removing the existing `oj-agent` service.
4. Wait for `oj-agent-tools`, `hermes`, `agent-runtime-gateway` and `learning-profile-scheduler` health checks.
5. Sign in with a test user and load the workspace. Confirm a `syncode-u<userId>` directory appears in the
   `hermes_data` volume.
6. Verify session creation, token streaming, an MCP-backed question lookup, stop, steer and approval denial.
7. Add a completed submission, wait for the scheduler, and verify exactly one `USER.md` candidate appears; reject
   it once, then repeat with newer learning data and verify approval changes `USER.md`.
8. Register a second test Runtime name, activate it, and verify an old session stays on the old Runtime while
   a new session is created on the new Runtime.
9. Monitor the new path before retiring old `/api/ai/*` compatibility routes and their database tables.

Rollback can point the UI back to the compatibility routes without deleting `hermes_data`. Do not remove
`hermes_data` or `runtime_gateway_data` during routine deploys, rollbacks or image upgrades.

## Failure behavior

- If profile provisioning fails, the gateway returns an error and does not route the user to another profile.
- If the active Runtime is unavailable, only a new session or sessionless Run may fail over to another registered
  healthy Runtime. Existing sessions never move, and there is no Direct DeepSeek fallback.
- If candidate activation health-check fails, the current active Runtime remains unchanged.
- If an MCP call fails, Hermes receives the native tool error and decides how to explain or retry it.
- If a tool requires approval, Hermes pauses the run and the UI relays the user's once/deny decision.
- If an SSE connection ends with a Hermes terminal event, that event is the source of truth for the displayed
  result.

This keeps one agent loop, one context/memory owner and one tool-execution owner: whichever Runtime owns the
session. For the initial adapter, that owner is Hermes. SynCode stores only protocol projections and authenticated
review decisions; it never performs model inference or executes a model-selected tool on Hermes' behalf.
