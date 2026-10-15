import assert from "node:assert/strict";

import {
  enforceHermesRunRateLimit,
  parseHermesRunRequest,
  resetHermesRunRateLimitsForTests
} from "../lib/hermes-run-contract";
import { HermesProxyError } from "../lib/hermes-server";

async function rejects(body: unknown, status: number) {
  await assert.rejects(
    () => parseHermesRunRequest(new Request("http://localhost", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    })),
    (error) => error instanceof HermesProxyError && error.status === status
  );
}

async function main() {
  const parsed = await parseHermesRunRequest(new Request("http://localhost", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ input: "  explain this  ", instructions: "context", session_id: "session_123" })
  }));
  assert.deepEqual(parsed, {
    input: "explain this",
    instructions: "context",
    session_id: "session_123"
  });

  await rejects({ input: "hello", model: "attacker-model" }, 400);
  await rejects({ input: "hello", toolsets: ["terminal"] }, 400);
  await rejects({ input: "hello", hosted_room_dispatch: {} }, 400);
  await rejects({ input: "", session_id: "session_123" }, 400);
  await rejects({ input: "hello", session_id: "../other-profile" }, 400);
  await rejects({ input: "x".repeat(8_001) }, 413);

  resetHermesRunRateLimitsForTests();
  enforceHermesRunRateLimit("7", 1_000, 2);
  enforceHermesRunRateLimit("7", 1_001, 2);
  assert.throws(
    () => enforceHermesRunRateLimit("7", 1_002, 2),
    (error) => error instanceof HermesProxyError && error.status === 429
  );
  enforceHermesRunRateLimit("7", 61_001, 2);
}

void main();
