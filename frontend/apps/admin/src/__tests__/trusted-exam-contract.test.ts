import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const operations = readFileSync(
  fileURLToPath(new URL("../components/admin-exam-operations.tsx", import.meta.url)),
  "utf8"
);
const editor = readFileSync(
  fileURLToPath(new URL("../components/admin-exam-editor.tsx", import.meta.url)),
  "utf8"
);
const route = readFileSync(
  fileURLToPath(new URL("../app/api/trusted-exams/[...segments]/route.ts", import.meta.url)),
  "utf8"
);

for (const contract of [
  "candidates",
  "monitor",
  "grades",
  "results/release",
  "evidence",
  "Idempotency-Key"
]) {
  assert.ok(operations.includes(contract), `administrator workspace lost contract: ${contract}`);
}

for (const contract of ["latestStartTime", "durationMinutes", "resultReleasePolicy", "expectedRowVersion"]) {
  assert.ok(editor.includes(contract), `exam editor lost rule field: ${contract}`);
}

assert.ok(route.includes("/^[a-zA-Z0-9-]+$/"), "administrator BFF must reject unsafe path segments");
assert.ok(route.includes('"idempotency-key"'), "administrator BFF must forward idempotency keys");
assert.ok(operations.includes("Array.isArray(nextEvidence)"), "evidence panel must tolerate an empty backend payload");
