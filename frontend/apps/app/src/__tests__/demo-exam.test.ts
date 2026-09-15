import assert from "node:assert/strict";

import { createDemoExamAccess, createDemoExamAttempt } from "../components/demo-trusted-exam";

const access = createDemoExamAccess("exam-sprint-01");
assert.equal(access.title, "实验室招新编程体验考试");
assert.equal(access.canStart, true);
assert.equal(access.canResume, false);
assert.match(access.privacyNotice, /不创建真实考试记录/);

const attempt = createDemoExamAttempt("exam-sprint-01");
assert.equal(attempt.status, "IN_PROGRESS");
assert.equal(attempt.questions.length, 3);
assert.equal(attempt.questions.reduce((total, question) => total + question.score, 0), 100);
assert.ok(attempt.questions.every((question) => question.allowedLanguages.includes("java")));
assert.ok(attempt.questions.every((question) => question.starterCode.java.includes("public class Main")));

const submitted = createDemoExamAttempt("exam-sprint-01", {
  status: "SUBMITTED",
  serverNow: "2026-09-15T12:00:00.000Z",
  deadlineAt: "2026-09-15T13:30:00.000Z",
  submittedAt: "2026-09-15T12:45:00.000Z"
});
assert.equal(submitted.status, "SUBMITTED");
assert.equal(submitted.submittedAt, "2026-09-15T12:45:00.000Z");
