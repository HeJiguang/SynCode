# Phase 1 Exam API and Error Contract

Status: Accepted for Phase 1 implementation  
Date: 2026-09-13  
Depends on: `phase1-trusted-exam-domain.md`

## 1. Purpose

This contract gives the Java services, Next.js BFF routes, and browser pages one stable interpretation of exam state, errors, time, idempotency, and concurrency.

It applies to new Phase 1 exam endpoints. Existing endpoints remain available during migration, but new UI flows must not infer behavior from Chinese error messages or silently fall back to mock data.

## 2. Transport rules

- External APIs use HTTPS and JSON encoded as UTF-8.
- Resource identifiers are serialized as decimal strings in JSON to avoid JavaScript integer precision loss.
- Timestamps are ISO 8601 UTC instants with milliseconds.
- The authenticated user comes from the access token. A body or query `userId` never selects the acting candidate.
- Mutations use `POST`, `PUT`, or `DELETE`; `GET` is read-only.
- New resource paths use nouns. Action endpoints are reserved for domain commands such as `publish`, `start`, and `finalize`.
- Request and response bodies use camel case. Database names never leak into the API.
- Hidden judge cases, correct answers, internal risk thresholds, stack traces, and secrets are never returned.

Required headers:

| Header | Direction | Rule |
| --- | --- | --- |
| `Authorization` | Request | Existing bearer token contract |
| `X-Request-ID` | Both | Accept a valid client UUID or generate one at the gateway; propagate through BFF, services, logs, queue, and response |
| `Idempotency-Key` | Request | Required for publish, start, final submit, cancellation, and result release; UUID recommended, maximum 64 ASCII characters |
| `Retry-After` | Response | Included for rate limits or temporarily unavailable dependencies when a useful retry delay is known |

The BFF must forward `X-Request-ID` and `Idempotency-Key` unchanged. It must not retry a mutation unless the operation is idempotent and the same key is reused.

## 3. Canonical envelope

The existing numeric `code`, `msg`, and `data` fields are retained for compatibility. All new exam endpoints add request correlation and authoritative server time.

Success:

```json
{
  "code": 1000,
  "msg": "操作成功",
  "data": {},
  "requestId": "5ea4deca-1287-49f1-9b2c-da720a1baf40",
  "serverTime": "2026-09-13T09:15:30.125Z"
}
```

Failure:

```json
{
  "code": 3229,
  "msg": "答案已在其他请求中更新",
  "data": null,
  "requestId": "5ea4deca-1287-49f1-9b2c-da720a1baf40",
  "serverTime": "2026-09-13T09:15:30.125Z",
  "details": {
    "currentVersion": 8,
    "currentContentHash": "sha256:..."
  }
}
```

Rules:

- `code` is the machine contract. It is stable after release.
- `msg` is a safe fallback for logs and UI; clients do not branch on it.
- `data` is present on success and is `null` on failure.
- `details` is optional, code-specific, safe to show to the current actor, and contains no stack trace.
- `requestId` and `serverTime` are present on every new exam response, including failures.
- Paginated results use `data.items`, `data.page`, `data.pageSize`, and `data.total`; new endpoints do not create another top-level envelope shape.

The BFF returns the same envelope and HTTP status to the browser. Page code uses one shared `ExamApiError` type with `code`, `httpStatus`, `requestId`, `details`, and safe message.

## 4. HTTP status mapping

HTTP status describes the transport/domain class. Numeric `code` describes the precise business outcome.

| HTTP | Meaning |
| --- | --- |
| 200 | Successful query or idempotent command, including a replayed command |
| 201 | Resource created when the distinction is useful; replay returns 200 with the same resource |
| 202 | Accepted asynchronous judge/aggregation command |
| 400 | Malformed JSON, invalid type, or syntactically invalid input |
| 401 | Missing, invalid, or expired authentication |
| 403 | Authenticated actor lacks permission or candidate authorization |
| 404 | Resource does not exist or must be concealed from this actor |
| 409 | Current state, idempotency key, session, or optimistic version conflict |
| 410 | Exam/attempt is cancelled or the allowed operation has permanently expired |
| 422 | Structurally valid command fails business validation, such as an incomplete exam draft |
| 429 | Rate or configured operation limit exceeded |
| 500 | Unexpected server error; response is sanitized and request id is logged |
| 502 | Invalid/unavailable upstream response at the BFF or gateway |
| 503 | Required service temporarily unavailable |

The Java exception handler must return the mapped status for new exam exceptions. The Next.js BFF preserves it. Catch-all conversion to HTTP 400 is prohibited.

## 5. Error code allocation

Existing codes `1000`, `2000`, `3000-3210`, and other current ranges remain unchanged. Phase 1 reserves `3220-3299` for trusted exam behavior.

| Code | Symbol | HTTP | Client behavior |
| --- | --- | --- | --- |
| 3220 | `EXAM_STATE_CONFLICT` | 409 | Refresh exam representation and disable invalid action |
| 3221 | `EXAM_NOT_PUBLISHED` | 409 | Return to exam list or admin draft |
| 3222 | `EXAM_CANCELLED` | 410 | Show terminal cancellation state and reason if visible |
| 3223 | `EXAM_ACCESS_TOO_EARLY` | 409 | Show server-based opening time; allow later retry |
| 3224 | `EXAM_ADMISSION_CLOSED` | 410 | Block new start; an existing in-progress attempt may still resume |
| 3225 | `EXAM_CANDIDATE_NOT_AUTHORIZED` | 403 | Block access; do not offer retry loop |
| 3226 | `EXAM_ATTEMPT_NOT_FOUND` | 404 | Offer start only when the access-check response allows it |
| 3227 | `EXAM_ATTEMPT_TERMINAL` | 409 | Replace editor with terminal receipt |
| 3228 | `EXAM_ATTEMPT_EXPIRED` | 410 | Refresh and show server-confirmed timeout receipt |
| 3229 | `EXAM_ANSWER_VERSION_CONFLICT` | 409 | Compare hashes/versions; never overwrite automatically |
| 3230 | `EXAM_IDEMPOTENCY_CONFLICT` | 409 | Stop retry; generate a new key only for a genuinely new command |
| 3231 | `EXAM_SUBMISSION_LIMIT_REACHED` | 429 | Disable submission and show remaining policy |
| 3232 | `EXAM_RESULT_NOT_RELEASED` | 403 | Hide score and show release policy/time when allowed |
| 3233 | `EXAM_GRADE_NOT_READY` | 409 | Show processing state and poll with backoff |
| 3234 | `EXAM_PUBLISH_VALIDATION_FAILED` | 422 | Render structured validation issues in the admin editor |
| 3235 | `EXAM_COMMAND_IN_PROGRESS` | 409 | Poll command/resource state using the same request id |
| 3236 | `EXAM_SESSION_CONFLICT` | 409 | Require explicit session takeover or return to current session |
| 3237 | `EXAM_ANSWER_NOT_FOUND` | 404 | Refresh attempt data |
| 3238 | `EXAM_QUESTION_NOT_IN_VERSION` | 404 | Refresh attempt; log possible stale/tampered route |
| 3239 | `EXAM_INTEGRITY_EVENT_REJECTED` | 422 | Drop only invalid event; keep the exam usable and log client diagnostics |
| 3240 | `EXAM_FINALIZATION_PENDING` | 202 | Show finalizing state; poll terminal receipt |

Validation `details` uses a stable structure:

```json
{
  "violations": [
    {
      "field": "questions[1].score",
      "rule": "positive",
      "message": "题目分值必须大于 0"
    }
  ]
}
```

`field` and `rule` are machine-readable. `message` is display fallback only.

## 6. Idempotency contract

- Keys are scoped by command type and authenticated actor.
- The server stores a canonical request hash with the key.
- Same key and same hash returns the original status/resource and `data.replayed: true`.
- Same key and different hash returns `3230 EXAM_IDEMPOTENCY_CONFLICT`.
- An uncertain network result is retried with the same key.
- A user intentionally repeating an action uses a new key only when the previous action has a terminal failure that permits a new command.
- Stored keys live at least through the exam result-release retention window for high-value exam commands.

Autosave uses optimistic concurrency instead of an idempotency key. Its `expectedVersion` protects against out-of-order requests.

## 7. Candidate endpoint contract

All paths shown are Java service paths behind the existing `/friend` gateway prefix. Next.js exposes same-purpose BFF routes under `/app/api/exams` without changing semantics.

| Method and path | Purpose | Important outcome |
| --- | --- | --- |
| `GET /exam/{examId}/access` | Preflight access and schedule check | Eligibility, server time, allowed action; no hidden questions |
| `POST /exam/{examId}/attempts/start` | Atomically start or replay start | Attempt, immutable questions, deadline, saved answers |
| `GET /exam/{examId}/attempts/current` | Resume current attempt | Full current server representation or explicit absence |
| `POST /exam/attempts/{attemptId}/heartbeat` | Reconcile time/session and activity | Server time, deadline, state, session warnings |
| `PUT /exam/attempts/{attemptId}/answers/{versionQuestionId}` | Versioned autosave | New answer version/hash/saved time |
| `POST /exam/attempts/{attemptId}/submissions` | Run or formally submit one frozen answer version | 202 plus judge request id |
| `POST /exam/attempts/{attemptId}/finalize` | Final submit, idempotently | Terminal or finalizing receipt |
| `GET /exam/attempts/{attemptId}/receipt` | Read finalization/grade processing state | Terminal timestamps and processing status |
| `POST /exam/attempts/{attemptId}/integrity-events` | Append a retry-safe event batch | Accepted and rejected sequence numbers |
| `GET /exam/{examId}/result` | Read released result | Current grade revision only when visible |

### Start request and response

```json
{
  "sessionId": "b78e1035-55ec-461d-a6ee-d7d989e8df46",
  "client": {
    "timezone": "Asia/Shanghai",
    "viewport": "1440x900"
  }
}
```

```json
{
  "attemptId": "90000000000001",
  "examId": "30001",
  "versionId": "80000000000001",
  "status": "IN_PROGRESS",
  "startedAt": "2026-09-13T09:00:00.000Z",
  "deadlineAt": "2026-09-13T10:30:00.000Z",
  "replayed": false,
  "questions": [],
  "answers": []
}
```

Question objects contain `versionQuestionId`; later calls do not accept mutable `questionId` as the runtime identity.

### Autosave request and response

```json
{
  "expectedVersion": 7,
  "answerType": "CODE",
  "language": "java17",
  "content": "public class Main { ... }",
  "contentHash": "sha256:..."
}
```

```json
{
  "answerId": "91000000000001",
  "answerVersion": 8,
  "contentHash": "sha256:...",
  "savedAt": "2026-09-13T09:15:30.125Z"
}
```

The first save uses `expectedVersion: 0`. On `3229`, the server returns current version/hash; the browser preserves its unsaved local content and asks the user to resolve a real content conflict.

### Finalize response

```json
{
  "attemptId": "90000000000001",
  "status": "SUBMITTED",
  "finalizationReason": "CANDIDATE_SUBMIT",
  "submittedAt": "2026-09-13T10:12:05.004Z",
  "gradeStatus": "PROCESSING",
  "replayed": false
}
```

Timeout returns the same shape with `status: "TIMED_OUT"` and `finalizationReason: "DEADLINE"`.

## 8. Administration endpoint contract

All paths are behind the existing `/system` gateway prefix.

| Method and path | Purpose |
| --- | --- |
| `POST /exam` | Create draft |
| `GET /exam/{examId}` | Read draft, current version, and allowed actions |
| `PUT /exam/{examId}` | Edit draft rules with optimistic row version |
| `PUT /exam/{examId}/questions` | Replace ordered draft composition atomically |
| `POST /exam/{examId}/publish` | Validate and create immutable version |
| `POST /exam/{examId}/withdraw` | Return pre-start publication to draft |
| `POST /exam/{examId}/cancel` | Terminal cancellation with reason |
| `PUT /exam/{examId}/candidates` | Add/revoke candidate authorizations in a validated batch |
| `GET /exam/{examId}/monitor` | Paginated attempt/session/last activity summary |
| `GET /exam/{examId}/grades` | Paginated current grade revisions and judge failures |
| `POST /exam/{examId}/grades/recalculate` | Idempotent asynchronous recalculation |
| `POST /exam/{examId}/results/release` | Release a complete grade revision |
| `GET /exam/attempts/{attemptId}/integrity-events` | Restricted evidence timeline |

The read representations include `allowedActions` calculated by the server. The UI may use them to render controls, but the command endpoint always rechecks authorization and state.

Publish validation failure returns code `3234` and all discovered safe violations in one response. Successful publication returns the immutable `versionId`, `versionNo`, content hash, publisher, and publication timestamp.

## 9. State representation

JSON emits symbolic states, not numeric database codes:

- Exam: `DRAFT`, `PUBLISHED`, `ACTIVE`, `FINISHED`, `RESULT_RELEASED`, `CANCELLED`.
- Attempt: `IN_PROGRESS`, `SUBMITTED`, `TIMED_OUT`, `CANCELLED`.
- Grade: `WAITING_FOR_JUDGE`, `READY`, `RELEASED`, `NEEDS_REVIEW`.
- Save: `SAVED`, `LOCAL_ONLY`, `SAVING`, `CONFLICT`, `READ_ONLY` is browser UI state and is not persisted as the answer state.

Unknown enum values are handled as unsupported contract versions and surfaced through telemetry. They are not silently mapped to an existing state.

## 10. BFF and browser rules

- The BFF parses the backend envelope even on non-2xx responses and preserves `code`, `msg`, `details`, `requestId`, and HTTP status.
- Connection failures become a distinct BFF `502` response with request id; they are not converted to a domain code.
- Test and production builds never fall back to mock exam, question, attempt, or grade data.
- Browser code branches on numeric code and symbolic state, never translated text.
- Browser code does not create authoritative timestamps or infer submission success after a timeout.
- A failed autosave keeps an encrypted-at-rest browser draft where supported, displays unsaved state, and retries with bounded exponential backoff.
- A final-submit network timeout keeps the same idempotency key and queries the receipt before another command.
- Page reload always calls the current-attempt endpoint before enabling editing.

## 11. Contract tests

Each endpoint requires tests at three layers:

1. Java controller/service test checks HTTP status, numeric code, ownership, server time, and state transition.
2. Shared TypeScript contract test checks serialization, enum handling, large string IDs, and error preservation.
3. Next.js route test checks headers, authentication, status/code pass-through, and absence of mock fallback.

Mandatory concurrency cases:

- Two simultaneous starts return one attempt.
- Start retry with same key returns the same attempt.
- Same idempotency key with a changed request returns `3230`.
- Out-of-order autosave returns `3229` and keeps the newer answer.
- Autosave racing timeout/final submit cannot modify a terminal attempt.
- Two final-submit requests create one finalization.
- A delayed judge result attaches only to its frozen answer version.

## 12. Compatibility rollout

1. Add envelope metadata fields; old clients ignore unknown JSON fields.
2. Add shared TypeScript types and error parsing before new BFF routes.
3. Add the new Java endpoints while existing `/getFirstQuestion`, `/preQuestion`, and `/nextQuestion` remain available.
4. Move the candidate exam page to start/resume and immutable question identifiers.
5. Move the admin editor to the new publication command.
6. Remove mock fallback in test/production.
7. Deprecate old navigation/publication endpoints after logs show no active callers.

Any change to a numeric code, state meaning, idempotency scope, timestamp authority, or terminal response requires a contract update and compatibility test before implementation.
