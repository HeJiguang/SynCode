import assert from "node:assert/strict";

import { buildExamCompositionPayload, parseDecimalIds, toExamApiDateTime, validateExamForm } from "../lib/exam-form";

const valid = {
  title: "实验室招新考试",
  startTime: "2026-09-17T09:00",
  latestStartTime: "2026-09-17T09:30",
  endTime: "2026-09-17T11:00",
  durationMinutes: "90",
  timezone: "Asia/Shanghai",
  maxFormalSubmissions: "10",
  resultReleasePolicy: "MANUAL",
  resultReleaseTime: ""
};

assert.deepEqual(validateExamForm(valid, new Date("2026-09-16T10:00:00+08:00")), {});
assert.equal(toExamApiDateTime(valid.startTime, valid.timezone), "2026-09-17 01:00:00");
assert.equal(buildExamCompositionPayload([{
  questionId: "2100059118632513538",
  score: 10,
  required: true,
  questionType: "PROJECT"
}])[0].questionId, "2100059118632513538", "snowflake IDs must not be converted to unsafe JavaScript numbers");
assert.deepEqual(parseDecimalIds("2100059105600811010, 10001 10001"), ["2100059105600811010", "10001"]);
assert.equal(parseDecimalIds("2100059105600811010,bad-id"), null);

const invalid = validateExamForm({
  ...valid,
  title: " ",
  latestStartTime: "2026-09-17T08:30",
  endTime: "2026-09-17T08:00",
  durationMinutes: "0",
  timezone: "Asia/Shanghai",
  maxFormalSubmissions: "1.5",
  resultReleasePolicy: "SCHEDULED",
  resultReleaseTime: ""
}, new Date("2026-09-16T10:00:00+08:00"));

for (const field of ["title", "latestStartTime", "endTime", "durationMinutes", "maxFormalSubmissions", "resultReleaseTime"] as const) {
  assert.ok(invalid[field], `${field} should be rejected`);
}

assert.ok(validateExamForm({ ...valid, timezone: "invalid/timezone" }).timezone);

const nonexistentDstTime = validateExamForm({
  ...valid,
  startTime: "2026-03-08T02:30",
  latestStartTime: "2026-03-08T03:30",
  endTime: "2026-03-08T04:30",
  timezone: "America/New_York"
}, new Date("2026-01-01T00:00:00Z"));
assert.match(nonexistentDstTime.startTime ?? "", /无效/);
