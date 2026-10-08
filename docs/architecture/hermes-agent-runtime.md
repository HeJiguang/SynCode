# Hermes Agent Runtime

Hermes is SynCode's agent core. It is not an LLM gateway hidden behind `oj-agent`.

```text
Browser
  -> authenticated Next.js Hermes proxy
     -> Hermes profile syncode-u<userId>
        -> Hermes sessions, memory, skills, agent loop, approvals and streaming
        -> SynCode HTTP MCP tools
           -> read-only OJ data scoped to the profile's userId
        -> DeepSeek
```

The workspace chat does not ask `oj-agent` to build prompts, parse model-produced tool JSON, execute a
second agent loop, poll Hermes, or fall back to a direct DeepSeek client. The old `oj-agent` routes remain
temporarily for migration compatibility, but they are not in the workspace chat path.

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
5. A user action invokes a Hermes skill, for example `/syncode-tutor`, and supplies the current workspace as
   factual `instructions`.
6. Next.js sends `POST /p/<profile>/v1/runs` and relays the native event stream from
   `GET /p/<profile>/v1/runs/<runId>/events`.
7. Hermes may call the SynCode MCP server itself. SynCode does not interpret a model response and then call
   the tool on Hermes' behalf.
8. Tokens, tool progress, approvals and terminal status are rendered directly from Hermes events.

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
across hosts.

## Skills and tools

Teaching behavior lives in versioned Hermes skills:

- `syncode-tutor`: progressive hints and explanation;
- `syncode-diagnosis`: evidence-based code and judge-result diagnosis;
- `syncode-training-plan`: a short plan based on the user's learning data.

The profile enables only Hermes' native memory toolset and the `syncode` MCP toolset on the API-server
surface. Broad host capabilities such as shell, files, browser, Docker and code execution are not enabled.

The SynCode MCP service currently exposes read-only tools:

- `get_question`
- `get_my_submission_history`
- `get_my_learning_profile`
- `get_my_current_training_plan`
- `search_practice_questions`

Each tool carries the MCP `readOnlyHint=true` annotation. The server is configured as `trust: untrusted`, so a
future tool without an explicit read-only annotation automatically enters Hermes' native approval flow.

## Services and configuration

Production adds two services alongside the compatibility `oj-agent` service:

- `hermes`: the official Hermes image extended only with SynCode skills; runs `gateway run`, multiplexes named
  profiles and keeps all Hermes state in `hermes_data`;
- `oj-agent-tools`: the existing Python image started with `app.mcp_gateway.server:app` on port 8016; serves
  MCP and the authenticated profile provision endpoint.

Stack-level secrets and settings:

```bash
HERMES_IMAGE=syncode-hermes:sha-...
HERMES_BASE_IMAGE=nousresearch/hermes-agent:latest
HERMES_MODEL=deepseek-chat
HERMES_DEEPSEEK_API_KEY=...
SYNCODE_HERMES_API_KEY=...
SYNCODE_HERMES_SESSION_SECRET=...
SYNCODE_HERMES_PROVISION_KEY=...
SYNCODE_MCP_SERVICE_KEY=...
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
`GATEWAY_MULTIPLEX_PROFILES=true` only on the private backend network. The official image entrypoint remains
intact because it initializes s6, repairs volume ownership and reconciles profiles.

## Rollout order

1. Generate the four SynCode secrets and a DeepSeek key; update both stack and runtime environment files.
2. Build `AGENT_IMAGE` and `HERMES_IMAGE`.
3. Deploy the stack without removing the existing `oj-agent` service.
4. Wait for `oj-agent-tools` and `hermes` health checks.
5. Sign in with a test user and load the workspace. Confirm a `syncode-u<userId>` directory appears in the
   `hermes_data` volume.
6. Verify session creation, token streaming, an MCP-backed question lookup, stop, steer and approval denial.
7. Monitor the new path before retiring old `/api/ai/*` orchestration routes and their database tables.

Rollback can point the UI back to the compatibility routes without deleting `hermes_data`. Do not remove that
volume during routine deploys, rollbacks or image upgrades; it contains the Hermes sessions and memory that
now form the user's agent state.

## Failure behavior

- If profile provisioning fails, Next.js returns 503 and does not route the user to another profile.
- If Hermes is unavailable, the workspace chat fails visibly; it does not silently use Direct DeepSeek.
- If an MCP call fails, Hermes receives the native tool error and decides how to explain or retry it.
- If a tool requires approval, Hermes pauses the run and the UI relays the user's once/deny decision.
- If an SSE connection ends with a Hermes terminal event, that event is the source of truth for the displayed
  result.

This keeps one agent loop, one memory owner and one tool-execution owner: Hermes.
