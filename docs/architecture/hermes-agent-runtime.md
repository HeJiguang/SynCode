# Hermes Agent Runtime

SynCode uses Hermes Agent as the primary agent runtime for tutor chat and training-plan generation. The existing OpenAI-compatible DeepSeek client remains available as a fallback and comparison baseline.

The user-visible Chat is owned by SynCode and persisted in MySQL. A Hermes session is runtime state only; it is never the source of truth for message history, ownership, memory, or permissions.

## Runtime boundary

```text
SynCode frontend
    -> oj-agent
       -> AgentRuntime
          -> HermesRuntime -> Hermes sidecar -> DeepSeek
          -> DirectRuntime ------------------> DeepSeek
```

`oj-agent` remains responsible for:

- authenticating the user and enforcing user/domain boundaries;
- assembling question, code, judge-result, and learning context;
- validating the model's JSON response;
- restricting training tasks to server-provided candidates;
- creating write intents and applying the existing draft/approval policy;
- persisting user-visible chats, Runs, ordered Run events, artifacts, immutable per-turn context, reviewed memories, and tool decisions;
- serializing runs for the same Chat while allowing different Chats and users to run concurrently;
- enforcing per-user active-run and creation-rate limits plus a process-wide execution-slot ceiling;
- preventing the agent runtime from directly accessing the database, judge containers, hidden tests, or the host shell.

Hermes is responsible for the agent loop, session history, context compression, provider routing, and run lifecycle.

## oj-agent configuration

Set these values in the `oj-agent` environment:

```bash
OJ_AGENT_RUNTIME_PROVIDER=hermes
OJ_AGENT_RUNTIME_FALLBACK_TO_DIRECT=true

OJ_AGENT_HERMES_BASE_URL=http://127.0.0.1:8642
OJ_AGENT_HERMES_API_KEY=replace-with-a-strong-sidecar-key
OJ_AGENT_HERMES_PROVIDER=deepseek
OJ_AGENT_HERMES_CHAT_MODEL=deepseek-v4-pro
OJ_AGENT_HERMES_TRAINING_MODEL=deepseek-v4-pro
OJ_AGENT_HERMES_REQUEST_TIMEOUT_SECONDS=10
OJ_AGENT_HERMES_RUN_TIMEOUT_SECONDS=90
OJ_AGENT_HERMES_POLL_INTERVAL_SECONDS=0.25

OJ_AGENT_AUTH_BASE_URL=http://oj-gateway:19090
OJ_AGENT_ALLOW_INSECURE_USER_ID_BODY=false
OJ_AGENT_CONVERSATION_SOFT_TOKEN_LIMIT=16000
OJ_AGENT_CONVERSATION_HARD_TOKEN_LIMIT=22000
OJ_AGENT_USER_MAX_ACTIVE_RUNS=3
OJ_AGENT_USER_RUN_RATE_LIMIT_PER_MINUTE=20
OJ_AGENT_ACTIVE_RUN_STALE_SECONDS=300
OJ_AGENT_GLOBAL_MAX_CONCURRENT_RUNS=16
OJ_AGENT_RUN_ADMISSION_WAIT_SECONDS=15
```

`OJ_AGENT_DATABASE_URL` may be set explicitly. Otherwise `oj-agent` builds a MySQL URL from `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_DATABASE`, `MYSQL_APP_USER`, and `MYSQL_PASSWORD`. SQLite is a local-development fallback only.

For automatic fallback, also configure the existing direct DeepSeek variables:

```bash
OJ_AGENT_LLM_PROVIDER=openai_compatible
OJ_AGENT_LLM_BASE_URL=https://api.deepseek.com/v1
OJ_AGENT_LLM_API_KEY=replace-with-your-deepseek-key
OJ_AGENT_CHAT_MODEL=deepseek-v4-pro
OJ_AGENT_TRAINING_MODEL=deepseek-v4-pro
```

Set `OJ_AGENT_RUNTIME_PROVIDER=direct` to bypass Hermes during incident recovery or A/B evaluation.

## Hermes sidecar

Configure the Hermes service account separately from `oj-agent`:

```bash
# ~/.hermes/.env inside the sidecar
API_SERVER_ENABLED=true
API_SERVER_KEY=replace-with-a-random-secret-of-at-least-16-characters
DEEPSEEK_API_KEY=replace-with-your-deepseek-key
```

Then start the gateway:

```bash
hermes gateway
```

The adapter uses `POST /v1/runs`, polls `GET /v1/runs/{run_id}`, and calls the stop endpoint after a timeout or a malformed approval request. Every create request includes an idempotency key.

## Chat and session continuity

Each user has one default learning Chat that continues while the user switches problems. The frontend restores its messages after refresh and exposes older Chats as read-only history. At the soft context limit it recommends rollover; at the hard limit it rejects additional turns until the user creates a continuation.

Before creating a continuation, the user reviews individual memory candidates. Only checked memories are copied into the new Chat, and the exact copied values remain visible in that Chat. Tool permissions are never copied as memory.

`oj-agent` hashes the user and Chat identifiers before sending `X-Hermes-Session-Key`, so raw identifiers are not exposed as Hermes memory keys. A new SynCode Chat always gets a new Hermes session.

The latest observed `conversationId -> sessionId` mapping is appended to `runtime-artifacts/hermes-sessions.jsonl`. Hermes still owns compression rotation: an old explicit session ID is resolved to the live continuation, and the stable session key lets Hermes recover the current session even when a local process has stale mapping state.

The same Chat is protected by an in-process lock and, on MySQL, a connection-scoped named lock. Different Chats and users are not serialized together.

## Multi-user run admission

Before an executable Run receives user-visible side effects, `oj-agent` performs admission under a MySQL named lock scoped to the user. The lock makes the active-run count and one-minute creation count atomic across service replicas. Rejected attempts are persisted as failed Runs with a `resource.limit_rejected` event, so abusive or misbehaving clients remain auditable and count toward the rate limit.

Admitted executable Runs are first marked `QUEUED` and emit `run.queued`. They acquire a bounded process-wide execution slot before transitioning to `RUNNING`; if no slot is available within the admission wait, the Run is marked failed and the API returns 503 with `Retry-After`. Active rows older than `OJ_AGENT_ACTIVE_RUN_STALE_SECONDS` no longer consume the user quota, which allows crashed workers to release quota without manual cleanup. The current path is a bounded inline queue; the durable request format and statuses remain compatible with a future dedicated worker pool.

## Authentication and ownership

Identity is resolved in this order:

1. trusted `X-User-Id` injected by the authenticated gateway;
2. bearer-token introspection through `OJ_AGENT_AUTH_BASE_URL` and `/friend/user/detail`;
3. request-body identity only when explicitly enabled for insecure local development.

Conversation, Run, artifact, event, memory, and tool-approval lookups all enforce ownership. Cross-user access returns 404 to avoid resource enumeration.

## Tool permissions and GitHub

Hermes built-in shell, filesystem, code execution, arbitrary network, package installation, Docker, secrets, raw database, and hidden-test tools are not user-approvable. If Hermes requests one, SynCode maps it to `host.shell`, sends `choice=deny` with the exact Hermes `request_id`, records the denial, and lets the Agent finish with a safe response. `session` and `always` approvals are never exposed.

Public GitHub access uses a separate SynCode-owned path:

1. validate an exact `https://github.com/{owner}/{repo}` public repository through `api.github.com`;
2. resolve and pin a full 40-character commit SHA;
3. persist a one-time, expiring approval and show it in the Chat;
4. after approval, download only from `codeload.github.com`;
5. reject path traversal, links, devices, submodules, Git LFS pointers, oversized archives, and excessive file counts;
6. create a temporary read-only context snapshot without installing dependencies or executing code.

Approved snapshot metadata and bounded text excerpts can be injected only into the owning Chat until expiry. Repository content is always treated as untrusted data.

The Run stores its normalized original request so a process restart does not discard the information needed to continue. Once every approval for a Run is resolved, `oj-agent` rebuilds `approved_tool_context` and resumes the original task in the same Hermes session. This continuation is an internal instruction, not another user-visible message. Approving and denying both resume the Agent; denial produces a constrained answer without the requested repository. A repeated request for the same repository and pinned commit reuses the resolved decision instead of opening an approval loop.

## Isolation requirements

The Hermes API server can expose terminal, file, browser, delegation, and other tools. Do not run the SynCode sidecar with the default broad toolset in production.

Minimum production controls:

- run Hermes in a dedicated container and as a non-root user;
- do not mount the Docker socket, source tree, secrets directories, or host filesystem;
- place Hermes on a private network reachable only by `oj-agent`;
- use a strong `API_SERVER_KEY` and never expose port `8642` publicly;
- disable `terminal`, `file`, `browser`, `code_execution`, `delegation`, `cronjob`, `computer_use`, `connections`, and other unused toolsets in Hermes configuration;
- restrict outbound access to the DeepSeek API and required observability endpoints;
- keep all database writes and judge actions behind SynCode write intents and policy checks.

Container isolation is the security boundary. A tool allowlist is defense in depth and must not be the only boundary.

## Failure behavior

- Hermes `completed`: validate the response through the existing SynCode schema and policy layers.
- Hermes `failed`, `cancelled`, or `interrupted`: use DirectRuntime when fallback is configured; otherwise fail the SynCode run.
- Hermes timeout: request `/stop`, then use the configured fallback.
- Hermes `waiting_for_approval`: deny host capabilities with the exact request ID and continue; malformed approval payloads stop the run.
- Invalid Hermes JSON: use DirectRuntime when fallback is configured.

The current SynCode endpoint still executes both the initial model turn and the post-approval continuation synchronously. A model-requested GitHub snapshot changes the durable Run to `WAITING_USER`; approving or denying the persisted request resumes the same logical Run and records the final assistant message, artifact, and events. A future worker/outbox path can make these turns asynchronous without changing the Chat or approval contracts.
