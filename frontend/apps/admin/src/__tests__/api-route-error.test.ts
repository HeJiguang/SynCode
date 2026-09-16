import assert from "node:assert/strict";

import { ApiError } from "@aioj/api";
import { resolveAdminApiError } from "../lib/api-route-error";

const validation = resolveAdminApiError(new ApiError("参数校验失败", 3002, {
  code: 3002,
  details: { violations: [{ field: "startTime", message: "考试开始时间不能为空" }] }
}), "考试保存失败。");
assert.equal(validation.status, 400);
assert.equal(validation.body.message, "参数校验失败");
assert.deepEqual(validation.body.details, {
  violations: [{ field: "startTime", message: "考试开始时间不能为空" }]
});

const conflict = resolveAdminApiError(new ApiError("考试状态不允许当前操作", 3220), "发布失败。");
assert.equal(conflict.status, 409);

const upstream = resolveAdminApiError(new Error("connect ETIMEDOUT"), "考试保存失败。");
assert.equal(upstream.status, 502);
