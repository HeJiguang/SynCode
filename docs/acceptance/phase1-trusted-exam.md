# Phase 1 Trusted Exam Acceptance

This checklist is the release gate for the first functional trusted-exam loop. Phase 1 supports Java programming questions; additional languages and question types are later phases.

## Automated gate

The revision is eligible for test deployment only when `ci.yml` passes all of the following:

- all Java reactor tests, including exam state, idempotency, timeout, grading, authorization, result visibility, and evidence rules;
- Python agent tests;
- candidate, administrator, shared API, and shared UI tests and production builds;
- MySQL 8 legacy preflight, Flyway baseline, first migrate, repeated migrate, validate, and post-migration verification;
- creation of a deploy bundle tied to the tested commit SHA.

After a successful `main` run, `cd-test.yml` deploys that exact bundle to the isolated test environment and checks the public site, candidate login, administrator login, and unauthenticated trusted-exam access boundary. Production remains manually approved through `cd.yml`.

## Functional acceptance script

Use one administrator and one candidate account in the test environment.

1. Create a draft exam with instructions, start/latest-entry/end times, duration, timezone, submission limit, and result policy.
2. Add at least two Java programming questions, set order, score, and required flags, then publish.
3. Confirm the published version number and content hash are present. Modify a source question and verify the published candidate paper remains unchanged.
4. Authorize the candidate. Confirm an unauthorized account receives a clear refusal.
5. Start the exam and record the Attempt id and server deadline. Refresh and confirm the same Attempt, deadline, questions, and latest drafts return.
6. Edit both questions, switch between them during an autosave, refresh, and confirm neither draft regresses. Disconnect briefly and confirm local drafts remain available and later synchronize.
7. Run one answer and formally submit it. Confirm the formal submission count decreases and the immutable answer version is recorded.
8. Trigger page blur, copy/paste, and a session takeover. Confirm the administrator evidence timeline shows event time, type, safe metadata, and risk points without clipboard text.
9. Submit the paper. Repeat the finalize request and confirm the same terminal receipt is returned and all answers remain frozen.
10. Run the reconciliation handler. Confirm expired in-progress Attempts become `TIMED_OUT`, completed submissions aggregate with snapshot scores, and a second run does not rebuild ready grades.
11. Confirm the candidate cannot see results before release. Review scores and evidence as administrator, publish results, and confirm the candidate can then see item and total scores.
12. Repeat with a scheduled release policy and confirm the reconciliation handler advances an ended exam and releases only after all current grades are ready.

## Failure and cancellation checks

- Withdraw a published exam before it starts and before any Attempt exists; it must return to draft.
- Once any Attempt exists, withdrawal must fail. Cancellation must terminate active Attempts, freeze answers, and create an audit event.
- A stale answer version must never overwrite a newer version.
- A late save or submit must first finalize the Attempt as timed out and then return the expiry error.
- An exam with no Attempts, or with any non-ready grade, must not release results.

## Evidence and privacy

The candidate notice states that session identifiers, salted network/browser summaries, and focus/fullscreen/copy/paste metadata are collected. Clipboard content is never stored. Integrity signals are evidence for manual review, not an automatic cheating verdict. The default evidence retention is 180 days; a school-specific policy must be configured and approved before production use.

## Deployment prerequisites

- A dedicated `syncode-test` self-hosted runner and GitHub `test` environment exist.
- Test and production secrets listed in `deploy/prod/env/github-secrets-guide.md` are configured.
- Test MySQL, Redis, RabbitMQ, Nacos, and judge workers are isolated from production.
- The XXL-Job administrator schedules `trustedExamReconciliationHandler` at least once per minute.
- Backup and rollback identifiers are recorded before production migration.

Cloud acceptance is complete only after the test workflow URL, commit SHA, migration version, smoke output, and manual functional script result are recorded in the local project plan.
