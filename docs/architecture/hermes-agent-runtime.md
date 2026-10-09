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
              -> Hermes sessions, memory, skills, agent loop, approvals and streaming
              -> SynCode HTTP MCP tools
                 -> read-only OJ data scoped to the profile's userId
              -> DeepSeek
```

The workspace chat does not ask `oj-agent` to build prompts, parse model-produced tool JSON, execute a
second agent loop, poll Hermes, or fall back to a direct DeepSeek client. The Runtime gateway only authenticates,
routes, translates IDs and streams bytes/events. The old `oj-agent` and `/api/ai/hermes/*` routes remain
temporarily for rollback compatibility, but they are not in the workspace chat path.

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
- a stable Runtime protocol for sessions, runs, event streams and run control;
- public ID ownership, the Runtime registry and atomic active-Runtime selection;
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

Production adds three services alongside the compatibility `oj-agent` service:

- `hermes`: the official Hermes image extended only with SynCode skills; runs `gateway run`, multiplexes named
  profiles and keeps all Hermes state in `hermes_data`;
- `oj-agent-tools`: the existing Python image started with `app.mcp_gateway.server:app` on port 8016; serves
  MCP and the authenticated profile provision endpoint;
- `agent-runtime-gateway`: the Python image started with `app.runtime_gateway.server:app` on port 8017;
  exposes the stable Runtime protocol and keeps its registry in `runtime_gateway_data`.

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

The stack injects these internal addresses into Next.js, the gateway and the provisioner:

```text
SYNCODE_AGENT_RUNTIME_BASE_URL=http://agent-runtime-gateway:8017
SYNCODE_AGENT_RUNTIME_API_KEY=<internal-gateway-key>
SYNCODE_AGENT_RUNTIME_SESSION_SECRET=<session-scope-secret>
SYNCODE_RUNTIME_DEFAULT_ADAPTER=hermes
SYNCODE_RUNTIME_DEFAULT_BASE_URL=http://hermes:8642
SYNCODE_RUNTIME_DEFAULT_PROVISION_URL=http://oj-agent-tools:8016/internal/profiles/ensure
SYNCODE_MCP_PUBLIC_URL=http://oj-agent-tools:8016/mcp
```

Hermes runs with `API_SERVER_HOST=0.0.0.0`, `API_SERVER_PORT=8642`, and
`GATEWAY_MULTIPLEX_PROFILES=true` only on the private backend network. The official image entrypoint remains
intact because it initializes s6, repairs volume ownership and reconciles profiles.

## Hot switching

The internal control plane is authenticated with `SYNCODE_RUNTIME_GATEWAY_KEY`:

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

## Rollout order

1. Generate the four SynCode secrets and a DeepSeek key; update both stack and runtime environment files.
2. Build `AGENT_IMAGE` and `HERMES_IMAGE`.
3. Deploy the stack without removing the existing `oj-agent` service.
4. Wait for `oj-agent-tools`, `hermes` and `agent-runtime-gateway` health checks.
5. Sign in with a test user and load the workspace. Confirm a `syncode-u<userId>` directory appears in the
   `hermes_data` volume.
6. Verify session creation, token streaming, an MCP-backed question lookup, stop, steer and approval denial.
7. Register a second test Runtime name, activate it, and verify an old session stays on the old Runtime while
   a new session is created on the new Runtime.
8. Monitor the new path before retiring old `/api/ai/*` compatibility routes and their database tables.

Rollback can point the UI back to the compatibility routes without deleting `hermes_data`. Do not remove
`hermes_data` or `runtime_gateway_data` during routine deploys, rollbacks or image upgrades.

## Failure behavior

- If profile provisioning fails, the gateway returns an error and does not route the user to another profile.
- If the active Runtime is unavailable, the workspace chat fails visibly; it does not silently use another
  Runtime or Direct DeepSeek.
- If candidate activation health-check fails, the current active Runtime remains unchanged.
- If an MCP call fails, Hermes receives the native tool error and decides how to explain or retry it.
- If a tool requires approval, Hermes pauses the run and the UI relays the user's once/deny decision.
- If an SSE connection ends with a Hermes terminal event, that event is the source of truth for the displayed
  result.

This keeps one agent loop, one memory owner and one tool-execution owner: whichever Runtime owns the session.
For the initial adapter, that owner is Hermes.
