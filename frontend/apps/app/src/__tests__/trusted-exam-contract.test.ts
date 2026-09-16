import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const workspace = readFileSync(
  fileURLToPath(new URL("../components/trusted-exam-workspace.tsx", import.meta.url)),
  "utf8"
);
const route = readFileSync(
  fileURLToPath(new URL("../app/api/trusted-exams/[...segments]/route.ts", import.meta.url)),
  "utf8"
);

for (const contract of [
  "serverNow",
  "deadlineAt",
  "expectedVersion",
  "attempts/${attempt.attemptId}/heartbeat",
  "attempts/${attempt.attemptId}/integrity-events",
  "attempts/${attempt.attemptId}/finalize",
  "window.localStorage",
  "for (const question of attempt.questions)"
]) {
  assert.ok(workspace.includes(contract), `candidate workspace lost contract: ${contract}`);
}

assert.ok(!workspace.includes("clipboardData"), "clipboard content must never be collected");
assert.match(workspace, /if \(!demoMode\) window\.localStorage\.removeItem/, "demo drafts must survive reloads");
assert.ok(route.includes("/^[a-zA-Z0-9-]+$/"), "trusted exam BFF must reject unsafe path segments");
assert.ok(
  route.includes('segments?.[0] === "exams" ? segments.slice(1) : segments'),
  "trusted exam BFF must map the frontend exams resource to the backend exam root"
);
assert.ok(route.includes('backendSegments.join("/")'), "trusted exam BFF must proxy normalized segments");
assert.ok(route.includes('"idempotency-key"'), "trusted exam BFF must forward idempotency keys");
