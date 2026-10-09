import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const panel = readFileSync(resolve(root, "components/ai-panel.tsx"), "utf8");
const helper = readFileSync(resolve(root, "lib/agent-runtime-server.ts"), "utf8");
const eventRoute = readFileSync(resolve(root, "app/api/ai/runtime/runs/[runId]/events/route.ts"), "utf8");

assert.match(panel, /\/ai\/runtime\/sessions/);
assert.match(panel, /\/ai\/runtime\/runs/);
assert.doesNotMatch(panel, /\/ai\/hermes/);
assert.doesNotMatch(panel, /Hermes(?:Session|Message|Event)/);
assert.doesNotMatch(panel, /\/syncode-(?:tutor|diagnosis|training-plan)/);
assert.match(panel, /workflow: WORKFLOW_BY_RUN_TYPE/);
assert.match(panel, /\/ai\/runtime\/memories/);
assert.match(panel, /\/ai\/runtime\/memory-candidates/);
assert.match(panel, /\/ai\/runtime\/context-candidates/);
assert.match(panel, /WAITING_FOR_CONTEXT_REVIEW/);
assert.match(panel, /review_kind === "context_summary"/);
assert.match(panel, /Last-Event-ID/);
assert.match(panel, /\/ai\/runtime\/runs\/\$\{encodeURIComponent\(runId\)\}/);

assert.match(helper, /SYNCODE_AGENT_RUNTIME_BASE_URL/);
assert.match(helper, /SYNCODE_AGENT_RUNTIME_API_KEY/);
assert.match(helper, /X-SynCode-User-ID/);
assert.doesNotMatch(helper, /SYNCODE_HERMES/);
assert.doesNotMatch(helper, /syncode-u/);
assert.match(helper, /rt\[rsmc\]/);
assert.match(eventRoute, /request\.headers\.get\("Last-Event-ID"\)/);
assert.match(eventRoute, /last_seq/);

for (const relative of [
  "app/api/ai/runtime/sessions/route.ts",
  "app/api/ai/runtime/sessions/[sessionId]/route.ts",
  "app/api/ai/runtime/sessions/[sessionId]/messages/route.ts",
  "app/api/ai/runtime/runs/route.ts",
  "app/api/ai/runtime/runs/[runId]/route.ts",
  "app/api/ai/runtime/runs/[runId]/events/route.ts",
  "app/api/ai/runtime/runs/[runId]/[action]/route.ts",
  "app/api/ai/runtime/memories/route.ts",
  "app/api/ai/runtime/memory-candidates/route.ts",
  "app/api/ai/runtime/memory-candidates/[candidateId]/[action]/route.ts",
  "app/api/ai/runtime/context-candidates/route.ts",
  "app/api/ai/runtime/context-candidates/[candidateId]/[action]/route.ts",
  "app/api/ai/runtime/runs/[runId]/artifacts/route.ts"
]) {
  assert.ok(readFileSync(resolve(root, relative), "utf8").length > 0, `${relative} must exist`);
}
