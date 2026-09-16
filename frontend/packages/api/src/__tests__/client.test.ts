import assert from "node:assert/strict";

import { ApiError, requestJson } from "../client";

async function main() {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => new Response(JSON.stringify({
    code: 3234,
    msg: "试卷未通过发布校验",
    details: { violations: [{ field: "questions", message: "试卷至少需要一道题" }] }
  }), { status: 422, headers: { "Content-Type": "application/json" } });

  try {
    await assert.rejects(
      requestJson("/system/exam/1/publish", { baseUrl: "http://localhost" }),
      (error: unknown) => {
        assert.ok(error instanceof ApiError);
        assert.equal(error.code, 3234);
        assert.equal(error.message, "试卷未通过发布校验");
        assert.deepEqual(error.payload, {
          code: 3234,
          msg: "试卷未通过发布校验",
          details: { violations: [{ field: "questions", message: "试卷至少需要一道题" }] }
        });
        return true;
      }
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
}

void main();
