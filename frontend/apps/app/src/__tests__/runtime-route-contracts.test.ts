import assert from "node:assert/strict";

import { DEFAULT_AGENT_API_BASE_URL, resolveAgentApiBaseUrl } from "../lib/agent-base-url";
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

  const originalAgentBaseUrl = process.env.AGENT_PUBLIC_BASE_URL;
  const originalSyncodeAgentBaseUrl = process.env.SYNCODE_AGENT_BASE_URL;

  try {
    delete process.env.AGENT_PUBLIC_BASE_URL;
    delete process.env.SYNCODE_AGENT_BASE_URL;
    assert.equal(resolveAgentApiBaseUrl(), DEFAULT_AGENT_API_BASE_URL);

    process.env.AGENT_PUBLIC_BASE_URL = "http://127.0.0.1:8016/";
    assert.equal(resolveAgentApiBaseUrl(), "http://127.0.0.1:8016");

    delete process.env.AGENT_PUBLIC_BASE_URL;
    process.env.SYNCODE_AGENT_BASE_URL = "http://127.0.0.1:18016/";
    assert.equal(resolveAgentApiBaseUrl(), "http://127.0.0.1:18016");
  } finally {
    if (typeof originalAgentBaseUrl === "string") {
      process.env.AGENT_PUBLIC_BASE_URL = originalAgentBaseUrl;
    } else {
      delete process.env.AGENT_PUBLIC_BASE_URL;
    }

    if (typeof originalSyncodeAgentBaseUrl === "string") {
      process.env.SYNCODE_AGENT_BASE_URL = originalSyncodeAgentBaseUrl;
    } else {
      delete process.env.SYNCODE_AGENT_BASE_URL;
    }
  }
}

void main();
