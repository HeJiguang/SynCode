import assert from "node:assert/strict";

import {
  buildJudgeResultParams,
  buildJudgeRunPayload,
  buildJudgeSubmitPayload,
  normalizeBackendLongId
} from "../lib/judge-route-contracts";

async function main() {
  assert.equal(normalizeBackendLongId("2040750992449384449"), "2040750992449384449");
  assert.equal(normalizeBackendLongId(" 2040750992449384449 "), "2040750992449384449");
  assert.equal(normalizeBackendLongId("two-sum"), null);

  const runPayload = buildJudgeRunPayload(
    {
      questionId: "2040750992449384449",
      examId: "2041108424049139714",
      customInputs: ["1 2"]
    },
    0,
    "class Solution {}"
  );
  assert.equal(runPayload?.questionId, "2040750992449384449");
  assert.equal(typeof runPayload?.questionId, "string");
  assert.equal(runPayload?.examId, "2041108424049139714");
  assert.deepEqual(runPayload?.customInputs, ["1 2"]);

  const submitPayload = buildJudgeSubmitPayload(
    {
      questionId: "2040750992449384449",
      examId: "2041108424049139714"
    },
    0,
    "class Solution {}"
  );
  assert.equal(submitPayload?.questionId, "2040750992449384449");
  assert.equal(typeof submitPayload?.questionId, "string");
  assert.equal(submitPayload?.examId, "2041108424049139714");

  const params = buildJudgeResultParams("2040750992449384449", "req-1", "2041108424049139714");
  assert.equal(params?.get("questionId"), "2040750992449384449");
  assert.equal(params?.get("examId"), "2041108424049139714");
  assert.equal(params?.get("requestId"), "req-1");

}

void main();
