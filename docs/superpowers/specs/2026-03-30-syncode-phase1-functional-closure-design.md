# SynCode Phase 1 Functional Closure Design

Date: 2026-03-30
Status: Draft for user review
Scope: `D:\Project\OnlineOJ\bite-oj-master\bite-oj-master`

## 1. Summary

This phase does not focus on deployment topology, CI/CD, or cloud rollout.
It focuses on one prerequisite question:

`Is the product itself functionally complete enough to deserve deployment?`

The current answer is:

- core backend capability is mostly present
- user-side real judge flow is largely wired
- admin-side backend APIs are mostly present
- frontend still contains several critical blockers, placeholders, and mock fallbacks

Phase 1 will close the highest-value functional gaps so the system becomes a real deployable product candidate rather than a mixed real-and-demo workspace.

## 2. Repo Truth

The current repo now contains three runnable frontend surfaces under `frontend/`:

- `frontend/apps/web`
- `frontend/apps/app`
- `frontend/apps/admin`

The frontend was copied from `.worktrees/syncode-product-frontend-mvp/frontend` into the root workspace so it can now be audited and evolved from the main repo.

Observed runtime truth from this audit:

- `web` starts and serves `/`
- `app` starts and serves `/app`
- `admin` starts, but its unauthenticated entry flow currently redirects into a broken `/admin/login` route

Observed backend truth from controller and API-layer inspection:

- `oj-friend` already exposes real user login, profile, problem browse, judge submit/result/history, public messages, training, and exam navigation primitives
- `oj-system` already exposes real admin login, question CRUD, exam CRUD, notice CRUD, and user status management
- `oj-ai` / `oj-agent` already expose real AI chat and streaming paths

This means the main issue is no longer "missing architecture." The main issue is incomplete functional closure between frontend pages and already-existing backend capabilities.

## 3. Goals

- Make `app` and `admin` real product surfaces, not partial demos.
- Remove misleading silent fallback behavior from authenticated product flows.
- Close the most visible user-facing gaps first.
- Only add backend APIs where the frontend is blocked by a real missing contract.
- Preserve existing working judge, websocket, login, and AI paths while filling the gaps around them.

## 4. Non-goals

- Production deployment assets
- Docker production stacks
- CI/CD workflows
- Domain design and HTTPS strategy
- Broad UI redesign beyond what is needed to support real behavior
- Re-architecting `oj-judge` execution internals in this phase

Those belong to the next phase, after the product is functionally honest.

## 5. Audit Conclusions

### 5.1 Already real and worth preserving

- email-code login and authenticated user context
- public problem browse and problem detail
- workspace run-code path
- async submit + websocket + poll fallback judge path
- user profile read/update/avatar flow
- admin-side question, exam, notice, and user-status backend APIs
- AI chat and AI streaming request path

### 5.2 Critical frontend blockers

- admin entry/login routing is broken
- exam detail/workspace page is placeholder-driven and not backed by real exam question flow
- training page is read-only even though backend supports plan generation and task completion
- AI panel bootstraps from mock messages rather than real conversation history or empty real state
- authenticated pages still rely on silent mock fallback in places where failures should be visible

### 5.3 Backend gaps exposed by the frontend

- no real exam-workspace aggregation contract for "current exam state"
- no AI conversation-history read API for workspace boot
- no admin metrics/dashboard API; current dashboard is derived from list sizes
- one unfinished user-facing question endpoint still returns `null`

## 6. Recommended Phase Decomposition

This phase should be implemented as one functional-closure package with four ordered workstreams:

1. `admin` routing and auth entry repair
2. user-side real-data hardening
3. exam/training closure
4. backend contract gap fill

The order matters because the first two expose whether the app can even be entered and trusted, while the latter two complete broader workflows.

## 7. Frontend Design

### 7.1 `admin` surface

The `admin` app must behave like a real protected product surface:

- unauthenticated access must reliably land on a working login page
- successful login must return to a working dashboard
- every linked CRUD page must resolve under the configured `basePath`

This phase does not require a visual redesign. It requires route correctness and page usability.

### 7.2 `app` authenticated experience

The current anonymous-versus-authenticated distinction is valid and should remain:

- anonymous users may browse public information
- authenticated users must get real data, not mock fallback pretending to be real

Rule for Phase 1:

- public browse pages may still degrade gracefully when a public backend call fails
- authenticated product pages must not silently drop to demo data
- instead, they should show an explicit data-unavailable or action-failed state

### 7.3 Workspace

The workspace is the strongest part of the current product and should remain the center of gravity.

Phase 1 changes here should be targeted:

- keep real run / submit / websocket / history behavior
- replace mock AI boot messages with either real history or an empty-state assistant prompt
- keep AI question, code-context, and judge-result integration intact

### 7.4 Exams

The exam list page can already show live data, but the exam detail/workspace page is still fake.

Phase 1 exam behavior must become:

- browse live exams
- enter an exam when required
- load the real first/current question for that exam
- navigate real previous/next question within the exam
- show exam-specific state instead of hardcoded timers and fixed sample problem content

The exam workspace does not need a second editor system. It should reuse the existing workspace/editor capabilities with exam-aware state.

### 7.5 Training

The training page already reads live current-plan data.
It must now support the backend actions that already exist:

- generate training plan
- finish or skip task

This should keep the UI simple:

- current plan summary
- task list
- one regenerate action
- per-task completion action

No extra planner abstraction is needed in this phase.

## 8. Backend Design

### 8.1 Preserve working contracts

Do not rewrite these areas unless needed to support the phase goals:

- user auth
- user profile
- run-code
- async judge submit
- judge result polling
- websocket result push
- admin CRUD endpoints that already match current frontend usage

### 8.2 Add only missing contracts

Backend additions in Phase 1 should be narrow and frontend-driven.

Required additions:

- exam-workspace support contract
  - enough data to open a real exam question flow without hardcoded content
  - either a dedicated aggregated endpoint or a small set of directly consumable endpoints already available through composition
- AI conversation bootstrap contract
  - preferably "recent messages for current user + problem context"
  - if conversation persistence is not ready, return explicit empty history instead of forcing mock content

Optional but desirable additions:

- admin dashboard metrics endpoint

### 8.3 Explicit cleanup of misleading unfinished endpoints

Any endpoint that is currently public-facing and returns `null` should either:

- be implemented
- be removed from frontend usage
- or return an explicit error instead of a false-success shape

The current `semiLogin/dbList` behavior is a concrete example of something that should not survive into a production-ready claim.

## 9. Data and Contract Rules

### 9.1 Frontend contract rule

Frontend view models may still compute presentation-friendly fields, but authenticated product flows must be rooted in real backend payloads.

### 9.2 Mock-data rule

After Phase 1:

- `web` may continue to use curated marketing/demo content
- anonymous browse pages may still have limited safe fallback
- authenticated `app` pages may not silently fallback to mock business data
- `admin` pages may not use mock CRUD data for core actions

### 9.3 Error-handling rule

When a real authenticated request fails:

- show a user-visible failure state
- do not replace missing reality with fake success

This rule matters more than visual polish in this phase.

## 10. Testing and Verification Strategy

Phase 1 success must be verified at three levels.

### 10.1 Frontend runtime verification

- `web` serves successfully
- `app` serves successfully under `/app`
- `admin` serves successfully under `/admin`
- admin unauthenticated redirect lands on a real login page

### 10.2 Contract verification

- each frontend server route under `frontend/apps/app/src/app/api` and `frontend/apps/admin/src/app/api` must map to a real backend endpoint
- each backend endpoint used in the UI must return the fields required by the page or route

### 10.3 Functional walkthrough verification

User-side walkthrough:

- send email code
- login
- browse problem list
- open problem detail
- run code
- submit async judge
- receive judge result by websocket or fallback polling
- update profile
- open training page and generate plan

Admin-side walkthrough:

- login
- open dashboard
- list questions
- create or edit question
- list exams
- create or publish exam
- list notices
- create or publish notice
- update user status

## 11. Success Criteria

Phase 1 is complete when all of the following are true:

- `admin` has a working login entry and working protected navigation
- `app` authenticated pages no longer rely on silent mock fallback for core user data
- exam page is no longer a hardcoded fake workspace
- training page supports real generate and task-finish actions
- AI panel no longer bootstraps from hardcoded mock conversation messages
- all page-linked backend routes used by the product are real and return usable data
- remaining missing capabilities are explicitly documented as non-blocking follow-ups rather than hidden behind fake UI

## 12. Out of Scope for the Next Phase Boundary

After this phase, the repo should move into:

- production hardening
- deployment assets
- CI/CD
- observability and health endpoints
- public rollout validation

Those should only begin after this phase proves the product is functionally real.
