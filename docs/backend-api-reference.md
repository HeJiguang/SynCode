# OnlineOJ Backend API Reference

Updated: 2026-03-29

This document is a backend-facing API inventory extracted from the current codebase.
It is meant to help development, integration, testing, and later API governance.

It is based on:

- `oj-modules/oj-system` controllers and DTOs
- `oj-modules/oj-friend` controllers, DTOs, and websocket config
- `oj-modules/oj-judge` controller
- `oj-modules/oj-ai` controller and request DTO
- `oj-gateway` auth filter and AI route config
- `oj-common/oj-common-core` response wrappers and shared constants

This document intentionally avoids guessing behavior that is not directly confirmed by code.

## 1. Scope

Covered in this document:

- admin backend APIs in `oj-system`
- user-facing business APIs in `oj-friend`
- judge service API in `oj-judge`
- AI chat APIs in `oj-ai`
- websocket judge-result push
- non-production test/demo endpoints

Not covered in detail:

- internal Feign/RPC interfaces
- MQ payload contracts
- database schema
- Redis key design

## 2. Base Paths

The repository structure and gateway auth logic indicate these module prefixes:

- `/system/...`
- `/friend/...`
- `/judge/...`
- `/ai/...`

Notes:

- `AuthFilter` checks `system` and `friend` path prefixes directly.
- AI gateway config explicitly maps public prefix `/ai` to target prefix `/api`.
- In some environments, an outer reverse proxy may additionally prepend `/api`, producing paths like `/api/friend/...`. This repo confirms the module prefixes, but the extra proxy prefix is deployment-specific.

Recommended convention for documentation and integration:

- treat `/system`, `/friend`, `/judge`, `/ai` as the service-level public prefixes
- if your gateway or frontend proxy adds `/api`, prepend it consistently in deployment docs

## 3. Auth

Authenticated HTTP endpoints use:

```http
Authorization: Bearer <token>
```

Auth behavior confirmed from `oj-gateway`:

- `/system/**` requires an authenticated admin user
- `/friend/**` requires an authenticated ordinary user unless the route is whitelisted
- gateway validates JWT and Redis session state
- gateway injects internal headers such as `X-User-Id` and `X-User-Key` to downstream services

Frontend or external callers should only send:

- `Authorization`

They should not send:

- `X-User-Id`
- `X-User-Key`

Public or semi-public routes confirmed by controller naming and repo notes:

- `POST /friend/user/sendCode`
- `POST /friend/user/code/login`
- `GET /friend/question/semiLogin/list`
- `GET /friend/question/semiLogin/dbList`
- `GET /friend/question/semiLogin/hotList`
- `GET /friend/exam/semiLogin/list`
- `GET /friend/exam/semiLogin/redis/list`
- likely `POST /system/sysUser/login`

WebSocket handshake supports token query fallback:

```text
ws://<host>/friend/ws/judge/result?token=Bearer%20<token>
```

or

```text
ws://<host>/friend/ws/judge/result?token=<token>
```

## 4. Common Response Shapes

### 4.1 Normal wrapper: `R<T>`

```json
{
  "code": 1000,
  "msg": "success",
  "data": {}
}
```

Rules:

- `code = 1000` means success
- non-`1000` means business failure
- gateway auth failure is also returned as JSON, typically `3001`

### 4.2 Paged wrapper: `TableDataInfo`

```json
{
  "code": 1000,
  "msg": "success",
  "rows": [],
  "total": 0
}
```

Shared pagination input:

- `pageNum`, default `1`
- `pageSize`, default `10`

### 4.3 Common result codes

Important shared codes:

- `1000`: success
- `2000`: generic business failure
- `3001`: unauthorized
- `3002`: parameter validation failure
- `3003`: not exists
- `3004`: already exists
- `3101` to `3111`: user/login/email/code related failures
- `3201` to `3208`: exam related failures
- `3301`: user already entered exam
- `3401` to `3402`: file upload failures
- `3501` to `3502`: first/last question navigation failures
- `3601`: unsupported program type
- `3701`: MQ produce failure

## 5. System Module: Admin APIs

Base path: `/system`

These endpoints are for admin/backend management.

### 5.1 Admin user auth: `/system/sysUser`

| Method | Path | Auth | Purpose | Key params/body | Response |
| --- | --- | --- | --- | --- | --- |
| `POST` | `/system/sysUser/login` | No | Admin login | body: `userAccount`, `password` | `R<String>` token |
| `DELETE` | `/system/sysUser/logout` | Yes, admin | Logout | header: `Authorization` | `R<Void>` |
| `GET` | `/system/sysUser/info` | Yes, admin | Current admin info | header: `Authorization` | `R<LoginUserVO>` |
| `POST` | `/system/sysUser/add` | Yes, admin | Create admin account | body: `userAccount`, `password` | `R<Void>` |
| `DELETE` | `/system/sysUser/{userId}` | Yes, admin | Delete admin account | path: `userId` | `R<Void>` |
| `GET` | `/system/sysUser/detail` | Yes, admin | Admin detail | query: `userId`, optional `sex` | `R<SysUserVO>` |

Implementation note:

- `DELETE /system/sysUser/{userId}` currently returns `null` in controller code.
- `GET /system/sysUser/detail` currently returns `null` in controller code.
- They should be treated as unfinished, not production-ready.

### 5.2 Ordinary user management: `/system/user`

| Method | Path | Auth | Purpose | Key params/body | Response |
| --- | --- | --- | --- | --- | --- |
| `GET` | `/system/user/list` | Yes, admin | User list | query DTO, plus common paging | `TableDataInfo` |
| `PUT` | `/system/user/updateStatus` | Yes, admin | Enable/disable user | body: `UserDTO` | `R<Void>` |

### 5.3 Exam management: `/system/exam`

| Method | Path | Auth | Purpose | Key params/body | Response |
| --- | --- | --- | --- | --- | --- |
| `GET` | `/system/exam/list` | Yes, admin | Exam list | query DTO, plus paging | `TableDataInfo` |
| `POST` | `/system/exam/add` | Yes, admin | Create exam | body: `title`, `startTime`, `endTime` | `R<String>` examId |
| `POST` | `/system/exam/question/add` | Yes, admin | Attach questions to exam | body: `examId`, `questionIdSet[]` | `R<Void>` |
| `DELETE` | `/system/exam/question/delete` | Yes, admin | Remove question from exam | query: `examId`, `questionId` | `R<Void>` |
| `GET` | `/system/exam/detail` | Yes, admin | Exam detail | query: `examId` | `R<ExamDetailVO>` |
| `PUT` | `/system/exam/edit` | Yes, admin | Edit exam | body: `examId`, `title`, `startTime`, `endTime` | `R<Void>` |
| `DELETE` | `/system/exam/delete` | Yes, admin | Delete exam | query: `examId` | `R<Void>` |
| `PUT` | `/system/exam/publish` | Yes, admin | Publish exam | query: `examId` | `R<Void>` |
| `PUT` | `/system/exam/cancelPublish` | Yes, admin | Cancel publish | query: `examId` | `R<Void>` |

### 5.4 Question management: `/system/question`

| Method | Path | Auth | Purpose | Key params/body | Response |
| --- | --- | --- | --- | --- | --- |
| `GET` | `/system/question/list` | Yes, admin | Question list | query DTO, plus paging | `TableDataInfo` |
| `POST` | `/system/question/add` | Yes, admin | Create question | body includes `title`, `difficulty`, `algorithmTag`, `knowledgeTags`, `estimatedMinutes`, `trainingEnabled`, `timeLimit`, `spaceLimit`, `content`, `questionCase`, `defaultCode`, `mainFuc` | `R<Void>` |
| `GET` | `/system/question/detail` | Yes, admin | Question detail | query: `questionId` | `R<QuestionDetailVO>` |
| `PUT` | `/system/question/edit` | Yes, admin | Edit question | body: `questionId` + same fields as add | `R<Void>` |
| `DELETE` | `/system/question/delete` | Yes, admin | Delete question | query: `questionId` | `R<Void>` |

## 6. Friend Module: User-Facing Business APIs

Base path: `/friend`

These endpoints back the product-facing OJ features.

### 6.1 User auth and profile: `/friend/user`

| Method | Path | Auth | Purpose | Key params/body | Response |
| --- | --- | --- | --- | --- | --- |
| `POST` | `/friend/user/sendCode` | No | Send email code | body: `email` | `R<Void>` |
| `POST` | `/friend/user/code/login` | No | Login by email code | body: `email`, `code` | `R<String>` token |
| `DELETE` | `/friend/user/logout` | Yes | Logout | header: `Authorization` | `R<Void>` |
| `GET` | `/friend/user/info` | Yes | Current login user info | header: `Authorization` | `R<LoginUserVO>` |
| `GET` | `/friend/user/detail` | Yes | Current user profile detail | no body | `R<UserVO>` |
| `PUT` | `/friend/user/edit` | Yes | Edit profile | body may include `nickName`, `sex`, `schoolName`, `majorName`, `phone`, `email`, `wechat`, `introduce`, `headImage` | `R<Void>` |
| `PUT` | `/friend/user/head-image/update` | Yes | Update avatar only | body: `headImage` | `R<Void>` |

### 6.2 User exam participation: `/friend/user/exam`

| Method | Path | Auth | Purpose | Key params/body | Response |
| --- | --- | --- | --- | --- | --- |
| `POST` | `/friend/user/exam/enter` | Yes | Enter an exam | header: `Authorization`, body: `examId` | `R<Void>` |
| `GET` | `/friend/user/exam/list` | Yes | My exam list | query DTO, plus paging | `TableDataInfo` |

Notes:

- `enter` is also guarded by `@CheckUserStatus`.

### 6.3 User messages: `/friend/user/message`

| Method | Path | Auth | Purpose | Key params/body | Response |
| --- | --- | --- | --- | --- | --- |
| `GET` | `/friend/user/message/list` | Yes | Current user message list | query: `pageNum`, `pageSize` | `TableDataInfo` |

### 6.4 Public and semi-public exam APIs: `/friend/exam`

| Method | Path | Auth | Purpose | Key params/body | Response |
| --- | --- | --- | --- | --- | --- |
| `GET` | `/friend/exam/semiLogin/list` | No or semi-login | Exam list | query DTO, plus paging | `TableDataInfo` |
| `GET` | `/friend/exam/semiLogin/redis/list` | No or semi-login | Exam list via Redis cache | query DTO, plus paging | `TableDataInfo` |
| `GET` | `/friend/exam/rank/list` | Usually yes or exam context | Exam rank list | query rank DTO | `TableDataInfo` |
| `GET` | `/friend/exam/getFirstQuestion` | Yes or exam context | First question of exam | query: `examId` | `R<String>` questionId |
| `GET` | `/friend/exam/preQuestion` | Yes or exam context | Previous question in exam | query: `examId`, `questionId` | `R<String>` questionId |
| `GET` | `/friend/exam/nextQuestion` | Yes or exam context | Next question in exam | query: `examId`, `questionId` | `R<String>` questionId |

### 6.5 Public and semi-public question APIs: `/friend/question`

| Method | Path | Auth | Purpose | Key params/body | Response |
| --- | --- | --- | --- | --- | --- |
| `GET` | `/friend/question/semiLogin/list` | No or semi-login | Question list | query DTO, plus paging | `TableDataInfo` |
| `GET` | `/friend/question/semiLogin/dbList` | No or semi-login | Question list via DB path | query DTO, plus paging | `TableDataInfo` |
| `GET` | `/friend/question/semiLogin/hotList` | No or semi-login | Hot question list | no body | `R<List<QuestionVO>>` |
| `GET` | `/friend/question/detail` | Usually yes | Question detail | query: `questionId` | `R<QuestionDetailVO>` |
| `GET` | `/friend/question/preQuestion` | Usually yes | Previous question | query: `questionId` | `R<String>` questionId |
| `GET` | `/friend/question/nextQuestion` | Usually yes | Next question | query: `questionId` | `R<String>` questionId |

Implementation note:

- `GET /friend/question/semiLogin/dbList` currently returns `null` in controller code.
- Treat it as unfinished.

### 6.6 Code submission and result APIs: `/friend/user/question`

| Method | Path | Auth | Purpose | Key params/body | Response |
| --- | --- | --- | --- | --- | --- |
| `POST` | `/friend/user/question/submit` | Yes | Synchronous submission | body: `examId`, `questionId`, `programType`, `userCode` | `R<UserQuestionResultVO>` |
| `POST` | `/friend/user/question/rabbit/submit` | Yes | Asynchronous submission through RabbitMQ | body: `examId`, `questionId`, `programType`, `userCode` | `R<AsyncSubmitResponseVO>` |
| `GET` | `/friend/user/question/exe/result` | Yes | Query execution result | query: `examId`, `questionId`, `currentTime`, `requestId` | `R<UserQuestionResultVO>` |
| `GET` | `/friend/user/question/submission/list` | Yes | Submission history | query: `examId`, `questionId` | `R<List<UserSubmissionHistoryVO>>` |

Submission notes:

- `programType` comment in DTO indicates `0 = java`, `1 = cpp`, `2 = golang`
- async submit should be paired with `requestId` tracking

### 6.7 File upload: `/friend/file`

| Method | Path | Auth | Purpose | Key params/body | Response |
| --- | --- | --- | --- | --- | --- |
| `POST` | `/friend/file/upload` | Yes | Upload file to OSS | multipart field: `file` | `R<OSSResult>` |

Consumes:

- `multipart/form-data`

### 6.8 Training APIs: `/friend/training`

| Method | Path | Auth | Purpose | Key params/body | Response |
| --- | --- | --- | --- | --- | --- |
| `GET` | `/friend/training/profile` | Yes | Training profile | no body | `R<TrainingProfile>` |
| `GET` | `/friend/training/current` | Yes | Current training plan | no body | `R<TrainingCurrentVO>` |
| `POST` | `/friend/training/generate` | Yes | Generate training plan | body optional: `targetDirection`, `preferredCount`, `basedOnExamId`, `sourceType` | `R<TrainingCurrentVO>` |
| `POST` | `/friend/training/task/finish` | Yes | Mark training task status | body: `taskId`, `taskStatus` | `R<Void>` |

## 7. WebSocket: Judge Result Push

WebSocket path inside friend module:

- `/friend/ws/judge/result`

Connection notes:

- gateway auth supports token in query string for websocket handshake
- websocket handler path is registered in `JudgeResultWebSocketConfig`
- current code allows all origins

Typical usage:

1. user submits code with `/friend/user/question/rabbit/submit`
2. server returns async response containing request tracking information
3. client subscribes on websocket
4. server pushes judge updates/results associated with that request

## 8. Judge Module

Base path: `/judge`

This looks like a service-facing judge endpoint rather than a public product API.

| Method | Path | Auth | Purpose | Key params/body | Response |
| --- | --- | --- | --- | --- | --- |
| `POST` | `/judge/doJudgeJavaCode` | Internal or trusted caller | Execute judge flow for Java submission | body: `JudgeSubmitDTO` | `R<UserQuestionResultVO>` |

Notes:

- controller name and method suggest this is infrastructure-facing
- there is no gateway/public usage guidance in repo for exposing it directly to browsers

## 9. AI Module

Base path:

- service controller path: `/chat`
- gateway public path inferred from config: `/ai/chat`

Gateway mapping note:

- `oj-gateway` local config shows public prefix `/ai`
- target prefix is rewritten to `/api`
- that means public `/ai/chat` maps to downstream `/api/chat`

### 9.1 AI request body

`AiChatRequest` fields:

- `questionTitle`
- `questionContent`
- `userCode`
- `judgeResult`
- `userMessage` required

### 9.2 AI endpoints

| Method | Public path | Auth | Purpose | Key params/body | Response |
| --- | --- | --- | --- | --- | --- |
| `POST` | `/ai/chat` | Depends on gateway deployment | Simple chat answer | body: `AiChatRequest` | `R<String>` |
| `POST` | `/ai/chat/detail` | Depends on gateway deployment | Structured chat answer | body: `AiChatRequest` | `R<AiChatDetailResponse>` |
| `POST` | `/ai/chat/stream` | Depends on gateway deployment | Streaming chat | body: `AiChatRequest` | `text/event-stream` |

Streaming notes:

- response content type is `text/event-stream`
- controller returns raw stream body, not `R<T>`

## 10. Test and Demo Endpoints

These should not be treated as stable product APIs.

### 10.1 System test

Base path: `/system/test`

Confirmed endpoints:

- `GET /system/test/list`
- `GET /system/test/add`
- `GET /system/test/redisAddAndGet`
- `GET /system/test/log`
- `GET /system/test/validation`
- `GET /system/test/apifoxtest`
- `POST /system/test/apifoxPost`

### 10.2 Friend test

Base path: `/friend/test`

Confirmed endpoints:

- `GET /friend/test/sendCode`
- `GET /friend/test/nginx/info`

## 11. Suggested Integration Order

For product/frontend integration, the most meaningful order is:

1. `/friend/user/sendCode`
2. `/friend/user/code/login`
3. `/friend/user/info`
4. `/friend/question/semiLogin/list`
5. `/friend/question/detail`
6. `/friend/user/question/submit`
7. `/friend/user/question/rabbit/submit`
8. `/friend/ws/judge/result`
9. `/friend/training/current`
10. `/ai/chat`

For admin/backend tooling, the most meaningful order is:

1. `/system/sysUser/login`
2. `/system/question/list`
3. `/system/question/add`
4. `/system/exam/add`
5. `/system/exam/question/add`
6. `/system/exam/publish`

## 12. Known Gaps and Risks

Documented directly from code:

- `GET /friend/question/semiLogin/dbList` returns `null`
- `DELETE /system/sysUser/{userId}` returns `null`
- `GET /system/sysUser/detail` returns `null`
- test controllers are still present in main source set
- websocket origin policy is fully open
- actual gateway white-list config comes from external configuration, so public-route coverage in this document is partly inferred from controller naming and comments

If needed, the next useful step would be generating an API table with example request and response payloads for each main business endpoint.
