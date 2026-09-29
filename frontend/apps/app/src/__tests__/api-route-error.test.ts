import assert from "node:assert/strict";

import { ApiError } from "@aioj/api";

import { resolveApiRouteError } from "../lib/api-route-error";

function main() {
  const rateLimit = resolveApiRouteError(
    new ApiError("\u5f53\u5929\u8bf7\u6c42\u6b21\u6570\u5df2\u8fbe\u5230\u4e0a\u9650", 3107),
    "\u9a8c\u8bc1\u7801\u53d1\u9001\u5931\u8d25\u3002"
  );
  assert.equal(rateLimit.status, 429);
  assert.equal(rateLimit.body.message, "\u5f53\u5929\u8bf7\u6c42\u6b21\u6570\u5df2\u8fbe\u5230\u4e0a\u9650");
  assert.equal(rateLimit.body.code, 3107);

  const conversationBusy = resolveApiRouteError(
    new ApiError("当前 Chat 正在处理另一条消息，请稍后重试。", 409),
    "AI 运行创建失败。"
  );
  assert.equal(conversationBusy.status, 409);
  assert.equal(conversationBusy.body.message, "当前 Chat 正在处理另一条消息，请稍后重试。");

  const invalidJson = resolveApiRouteError(
    new SyntaxError("Unexpected end of JSON input"),
    "\u9a8c\u8bc1\u7801\u53d1\u9001\u5931\u8d25\u3002"
  );
  assert.equal(invalidJson.status, 400);
  assert.equal(invalidJson.body.message, "\u8bf7\u6c42\u4f53\u4e0d\u662f\u5408\u6cd5\u7684 JSON\u3002");

  const upstreamFailure = resolveApiRouteError(
    new Error("connect ETIMEDOUT"),
    "\u9a8c\u8bc1\u7801\u53d1\u9001\u5931\u8d25\u3002"
  );
  assert.equal(upstreamFailure.status, 502);
  assert.equal(upstreamFailure.body.message, "connect ETIMEDOUT");
}

main();
