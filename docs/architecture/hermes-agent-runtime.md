# Hermes Agent Runtime

Hermes is SynCode's agent core. It is not an LLM gateway hidden behind `oj-agent`.

```text
Browser
  -> authenticated Next.js Hermes proxy
     -> Hermes profile syncode-u<userId>
        -> Hermes sessions, memory, skills, agent loop, approvals and streaming
        -> SynCode Memory Provider prefetch
           -> automatically recalled problem-solving and learning-state context
        -> SynCode HTTP MCP tools
           -> read-only OJ data scoped to the profile's userId
        -> DeepSeek
```

The workspace chat does not ask `oj-agent` to build prompts, parse model-produced tool JSON, execute a
second agent loop, poll Hermes, or fall back to a direct DeepSeek client. Legacy conversation, run, artifact,
approval and retrieval routes have been removed.

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
- the server-side mapping from a SynCode user to a Hermes profile;
- a transparent HTTP/SSE proxy so Hermes is never exposed publicly.

## Request flow

1. Next.js resolves the current user through `/friend/user/detail`.
2. The server maps that user to `syncode-u<userId>`. The browser cannot provide or override the profile.
3. The profile provision endpoint creates the Hermes profile atomically if this is the user's first request.
4. The UI creates or resumes a native Hermes session.
5. The UI sends the user's original request and supplies the current workspace as factual `instructions`.
   Hermes chooses a relevant Skill from its catalog and loads it through its native `skill_view` tool.
6. Next.js sends `POST /p/<profile>/v1/runs` and relays the native event stream from
   `GET /p/<profile>/v1/runs/<runId>/events`.
7. Before the first model call, Hermes `MemoryManager` invokes the profile's SynCode Memory Provider and
   injects relevant problem-solving and learning-state memory into the native memory context.
8. Hermes may call the SynCode MCP server itself. SynCode does not interpret a model response and then call
   the tool on Hermes' behalf.
9. Tokens, tool progress, approvals and terminal status are rendered directly from Hermes events.

Approvals, steer and stop are passed through to the matching native run endpoints. The unused session
`chat/stream` proxy is deliberately not exposed.

## User isolation

There is one named Hermes profile per SynCode user:

```text
/opt/data/profiles/syncode-u42
```

Next.js derives the name from the authenticated numeric user ID. There is no shared-profile fallback. Every
Hermes request uses the `/p/syncode-u42/...` route and a server-generated `X-Hermes-Session-Key` derived from
the user ID and `SYNCODE_HERMES_SESSION_SECRET`.

Hermes adds `X-SynCode-Hermes-Profile: syncode-u42` to every SynCode MCP request through its native
`identity_header` support. The MCP service validates the exact profile format and derives `userId=42`; tool
arguments never contain a model-selected user ID. A separate bearer key authenticates Hermes as the MCP
caller.

The named volume is mounted at `/opt/data` in Hermes and `/var/lib/hermes` in the profile provisioner. Both
containers use UID/GID 10000 and are constrained to the manager node so the local Swarm volume cannot split
across hosts. The separate `hermes_platform_skills` volume is writable only at
`/var/lib/hermes/platform-skills` in `oj-agent-tools` and read-only at
`/opt/platform-data/platform-skills` in Hermes.

## Skills and tools

Teaching behavior lives in versioned Hermes skills:

- `syncode-tutor`: progressive hints and explanation;
- `syncode-diagnosis`: evidence-based code and judge-result diagnosis;
- `syncode-training-plan`: a short plan based on the user's learning data;
- `syncode-learning-memory`: usage and evidence rules for automatically recalled learning memory.

The profile enables only Hermes' native memory toolset and the `syncode` MCP toolset on the API-server
surface. Broad host capabilities such as shell, files, browser, Docker and code execution are not enabled.

The SynCode MCP service currently exposes read-only tools:

- `get_question`
- `get_my_submission_history`
- `get_my_learning_profile`
- `get_my_current_training_plan`
- `search_practice_questions`
- `get_my_learning_memory_detail`
- `get_my_learning_state_memory_detail`

Each tool carries the MCP `readOnlyHint=true` annotation. The server is configured as `trust: untrusted`, so a
future tool without an explicit read-only annotation automatically enters Hermes' native approval flow.

## Native and structured learning memory

Hermes native memory remains the owner of conversational preferences, explicit goals and user-provided
background. SynCode maintains two changing, evidence-backed domains: problem-solving memory derived from
submissions and exams, and learning-state memory derived from problem episodes per knowledge tag. These stores
are intentionally separate: a statement such as "the user prefers progressive hints" is stable conversational
memory, while "binary-search mastery is improving with medium confidence" must be recomputed from recent evidence.

The learning-memory projector creates three levels: immutable submission and exam events, problem-session
and exam episodes, and recurring tag/error patterns. Each derived record points to lower-level evidence and
contains time, confidence and a lifecycle status (`active`, `improving`, or `resolved`). Submitted source code
is not copied into the projection or search index.

Hermes loads the `syncode-learning-memory` Memory Provider through its native `memory.provider` extension.
On every substantive turn, `MemoryManager.prefetch_all()` supplies the current user message to the provider,
which retrieves bounded pattern, episode, event and knowledge-state results through an internal authenticated
endpoint. Hermes injects the returned text into `<memory-context>` before the first model call. The model-visible
MCP surface only keeps `get_my_learning_memory_detail` and `get_my_learning_state_memory_detail` for evidence
expansion. The platform Skill tells diagnosis, tutoring and planning workflows how to use the context; no
external intent router is added.
Elasticsearch performs user-filtered BM25 and dense-vector retrieval for problem-solving memory with weighted
RRF. When that optional index is unavailable, structured database retrieval remains available and reports the
fallback mode explicitly.

See `docs/architecture/hermes-learning-memory.zh-CN.md` for the complete model and acceptance path.

## Personal and platform Skill evolution

Hermes remains the authoring engine for personal Skills. Its `background_review` process can create and
revise a Skill after a conversation, and a user can also teach or edit a Skill from the Skills workspace.
Every user writes to a separate profile directory:

```text
/opt/data/profiles/syncode-u42/skills
```

The governance scanner accepts Hermes background-review Skills (`created_by=agent`), user-taught Skills
(`created_by=learn`), and local handwritten Skills. It excludes the names in `.bundled_manifest`, packages
recorded by `.hub/lock.json`, and usage records marked `created_by=installed`. A malformed provenance file
stops that profile's synchronization without archiving its last known valid registry state. This prevents
bundled or downloaded packages from being mistaken for independently learned user experience.

Each accepted package is copied into an immutable database version, including `SKILL.md` and supported text
assets. Users can inspect versions, edit their active personal Skills, archive and restore them, or roll back
to an earlier snapshot. All reads and writes derive the profile from the authenticated numeric user ID;
client-supplied profile names cannot select another user's directory.

The platform catalog follows a reviewed promotion flow:

1. The hourly governance heartbeat synchronizes every profile and removes old or archived versions from the
   search index.
2. Elasticsearch indexes the de-identified description, category, full Skill content, and an embedding.
   BM25 and dense-vector searches run independently and are fused with reciprocal-rank fusion. A result must
   pass the configured fused-score threshold, and two Skills form an edge only when they are mutual neighbors
   owned by different users.
3. A connected group must contain at least three distinct users. The governance model receives only the
   redacted examples and produces a generalized, complete `SKILL.md`; it must remove user-specific paths,
   names, code, answers, and anecdotes.
4. The administrator sees the number of users, member Skills, recent uses, similarity method, de-identified
   source summaries, and the generated draft. The administrator may edit the name, category, content, and
   review note before publishing, or reject the candidate.
5. An approved package is written to `/var/lib/hermes/platform-skills`, versioned in the registry, and exposed
   to every Hermes profile through `/opt/platform-data/platform-skills`. Hermes mounts that catalog read-only;
   the user UI also refuses platform edits. A user may create a same-named personal Skill, which acts as a
   profile-local fork and never changes the platform release.

Publishing and lifecycle archiving compensate filesystem changes when the database transaction fails, so
Hermes cannot observe a release that has no audit record. Candidate identity includes the member versions;
when personal Skills improve, their new cluster can enter review without reopening an already published or
rejected historical candidate.

The event proxy records an invocation only when Hermes emits a native `skill_view` tool event. These events
provide per-version 30-day usage counts. By default, platform releases older than 30 days with at most one
recorded invocation enter an administrator lifecycle queue; both thresholds are configurable. The heartbeat
never deletes them automatically. An administrator can keep or archive the release, and every decision
records the administrator identity and note.

Automatic discovery requires all of the following settings:

```bash
SYNCODE_ELASTICSEARCH_URL=http://elasticsearch:9200
SYNCODE_SKILL_EMBEDDING_URL=https://embedding-provider/v1/embeddings
SYNCODE_SKILL_EMBEDDING_API_KEY=...
SYNCODE_SKILL_EMBEDDING_MODEL=...
SYNCODE_SKILL_EMBEDDING_DIMENSIONS=1024
SYNCODE_SKILL_MIN_RRF_SCORE=0.03
SYNCODE_PLATFORM_SKILL_STALE_DAYS=30
SYNCODE_PLATFORM_SKILL_MAX_USAGE_30D=1
```

The candidate synthesizer uses `SYNCODE_SKILL_GOVERNANCE_LLM_*` when set, otherwise it uses the configured
DeepSeek endpoint, key, and Hermes model. If Elasticsearch or embeddings are missing, personal versioning
continues, but the governance heartbeat is marked failed instead of claiming that semantic discovery ran.

The useful acceptance path is: three isolated users independently acquire similar personal Skills; one
heartbeat creates one reviewable draft; an administrator can compare its de-identified sources and publish
it; a fourth user can then see and use the platform Skill but cannot edit it; invocation events keep it out of
the stale queue, while an unused older release enters review and is archived only after an administrator acts.

## Services and configuration

Production runs three focused AI services:

- `hermes`: the official Hermes image extended only with SynCode skills; runs `gateway run`, multiplexes named
  profiles and keeps all Hermes state in `hermes_data`;
- `oj-agent-tools`: the existing Python image started with `app.mcp_gateway.server:app` on port 8016; serves
  MCP and the authenticated profile provision endpoint;
- `oj-agent`: exposes only the training-plan endpoint used by the Java training flow. Its planner uses the
  configured Hermes runtime and keeps the small session mapping in `agent_runtime_data`.

Stack-level secrets and settings:

```bash
HERMES_IMAGE=syncode-hermes:sha-...
HERMES_BASE_IMAGE=nousresearch/hermes-agent@sha256:861c9756ed6c558530c73d5c27860343b00c0d5efd6997a1d8ec6416c8a2b485
HERMES_MODEL=deepseek-chat
HERMES_DEEPSEEK_API_KEY=...
SYNCODE_HERMES_API_KEY=...
SYNCODE_HERMES_SESSION_SECRET=...
SYNCODE_HERMES_PROVISION_KEY=...
SYNCODE_MCP_SERVICE_KEY=...
SYNCODE_ELASTICSEARCH_URL=http://elasticsearch:9200
SYNCODE_SKILL_EMBEDDING_URL=...
SYNCODE_SKILL_EMBEDDING_API_KEY=...
SYNCODE_SKILL_EMBEDDING_MODEL=...
```

Use independent random values for the four SynCode secrets. `SYNCODE_HERMES_API_KEY` is the private Hermes
API bearer key, not the DeepSeek key. No Hermes port is published through Swarm ingress or nginx.

The stack injects these internal addresses into Next.js and the provisioner:

```text
SYNCODE_HERMES_BASE_URL=http://hermes:8642
SYNCODE_HERMES_PROVISION_URL=http://oj-agent-tools:8016/internal/profiles/ensure
SYNCODE_MCP_PUBLIC_URL=http://oj-agent-tools:8016/mcp
```

Hermes runs with `API_SERVER_HOST=0.0.0.0`, `API_SERVER_PORT=8642`, and
`GATEWAY_MULTIPLEX_PROFILES=true` only on the private `agent` network. The official image entrypoint remains
intact because it initializes s6, repairs volume ownership and reconciles profiles.

## Rollout order

1. Generate the four SynCode secrets and a DeepSeek key; update both stack and runtime environment files.
2. Build `AGENT_IMAGE` and `HERMES_IMAGE`.
3. Deploy the stack with the focused `oj-agent`, `oj-agent-tools` and `hermes` services.
4. Wait for `oj-agent-tools` and `hermes` health checks.
5. Sign in with a test user and load the workspace. Confirm a `syncode-u<userId>` directory appears in the
   `hermes_data` volume.
6. Verify session creation, token streaming, an MCP-backed question lookup, stop, steer and approval denial.
7. Generate a training plan and confirm the Java service can reach `oj-agent` directly.
8. Create similar personal Skills in three test profiles, run the governance heartbeat, review the generated
   candidate in `/admin/skills`, and confirm a fourth profile sees the platform Skill as read-only.

Do not remove `hermes_data` during routine deploys, rollbacks or image upgrades; it contains the Hermes
sessions and memory that form the user's agent state.

## Failure behavior

- If profile provisioning fails, Next.js returns 503 and does not route the user to another profile.
- If Hermes is unavailable, the workspace chat fails visibly; it does not silently use Direct DeepSeek.
- If an MCP call fails, Hermes receives the native tool error and decides how to explain or retry it.
- If a tool requires approval, Hermes pauses the run and the UI relays the user's once/deny decision.
- If an SSE connection ends with a Hermes terminal event, that event is the source of truth for the displayed
  result.

This keeps one agent loop, one memory owner and one tool-execution owner: Hermes.
