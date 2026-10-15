import { HermesProxyError } from "./hermes-server";

const RUN_FIELDS = new Set(["input", "instructions", "session_id"]);
const SESSION_ID_RE = /^[A-Za-z0-9._:-]{1,192}$/;
const MAX_BODY_BYTES = 64 * 1024;
const MAX_INPUT_CHARS = 8_000;
const MAX_INSTRUCTIONS_CHARS = 32_000;
const DEFAULT_RUNS_PER_MINUTE = 12;

export type HermesRunRequest = {
  input: string;
  instructions?: string;
  session_id?: string;
};

type RateWindow = {
  startedAt: number;
  count: number;
};

const runRateWindows = new Map<string, RateWindow>();

function boundedString(value: unknown, field: string, maxChars: number, required = false) {
  if (value === undefined && !required) return undefined;
  if (typeof value !== "string") {
    throw new HermesProxyError(`${field} 必须是字符串。`, 400);
  }
  const cleaned = value.trim();
  if (required && !cleaned) {
    throw new HermesProxyError(`${field} 不能为空。`, 400);
  }
  if (cleaned.length > maxChars) {
    throw new HermesProxyError(`${field} 超出长度限制。`, 413);
  }
  return cleaned;
}

export async function parseHermesRunRequest(request: Request): Promise<HermesRunRequest> {
  const declaredLength = Number(request.headers.get("content-length") ?? 0);
  if (Number.isFinite(declaredLength) && declaredLength > MAX_BODY_BYTES) {
    throw new HermesProxyError("Hermes 请求体超出大小限制。", 413);
  }

  const raw = await request.text();
  if (new TextEncoder().encode(raw).byteLength > MAX_BODY_BYTES) {
    throw new HermesProxyError("Hermes 请求体超出大小限制。", 413);
  }

  let value: unknown;
  try {
    value = JSON.parse(raw);
  } catch {
    throw new HermesProxyError("Hermes 请求必须是合法 JSON。", 400);
  }
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new HermesProxyError("Hermes 请求必须是 JSON 对象。", 400);
  }

  const body = value as Record<string, unknown>;
  const extraFields = Object.keys(body).filter((key) => !RUN_FIELDS.has(key));
  if (extraFields.length > 0) {
    throw new HermesProxyError(`Hermes 请求包含不允许的字段：${extraFields.join(", ")}。`, 400);
  }

  const input = boundedString(body.input, "input", MAX_INPUT_CHARS, true)!;
  const instructions = boundedString(body.instructions, "instructions", MAX_INSTRUCTIONS_CHARS);
  const sessionId = boundedString(body.session_id, "session_id", 192);
  if (sessionId && !SESSION_ID_RE.test(sessionId)) {
    throw new HermesProxyError("session_id 格式无效。", 400);
  }

  return {
    input,
    ...(instructions ? { instructions } : {}),
    ...(sessionId ? { session_id: sessionId } : {})
  };
}

function configuredRunsPerMinute() {
  const parsed = Number(process.env.SYNCODE_HERMES_RUNS_PER_MINUTE ?? DEFAULT_RUNS_PER_MINUTE);
  return Number.isInteger(parsed) && parsed > 0 && parsed <= 600 ? parsed : DEFAULT_RUNS_PER_MINUTE;
}

export function enforceHermesRunRateLimit(
  userId: string,
  now = Date.now(),
  limit = configuredRunsPerMinute()
) {
  const windowMs = 60_000;
  const current = runRateWindows.get(userId);
  if (!current || now - current.startedAt >= windowMs) {
    runRateWindows.set(userId, { startedAt: now, count: 1 });
  } else {
    if (current.count >= limit) {
      throw new HermesProxyError("Hermes 请求过于频繁，请稍后再试。", 429);
    }
    current.count += 1;
  }

  if (runRateWindows.size > 10_000) {
    for (const [key, window] of runRateWindows) {
      if (now - window.startedAt >= windowMs) runRateWindows.delete(key);
    }
  }
}

export function resetHermesRunRateLimitsForTests() {
  runRateWindows.clear();
}
