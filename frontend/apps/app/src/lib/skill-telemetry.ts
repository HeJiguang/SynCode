import { createHash } from "node:crypto";

import type { HermesRequestContext } from "./hermes-server";

const RESOURCE_RE = /^[A-Za-z0-9._:-]{1,192}$/;
const SKILL_RE = /^[a-z0-9][a-z0-9_-]{0,63}$/;

export type SkillTelemetryEvent = {
  event_id: string;
  event_type: "skill.invoked";
  occurred_at: string;
  run_id: string;
  session_id?: string;
  skill_name: string;
  payload: { tool: "skill_view" };
};

type ParsedSseEvent = {
  id?: string;
  payload: Record<string, unknown>;
};

function resource(value: unknown) {
  return typeof value === "string" && RESOURCE_RE.test(value) ? value : undefined;
}

function telemetryEventId(runId: string, suffix: string) {
  const raw = `${runId}:${suffix}`;
  if (raw.length <= 192) return raw;
  const digest = createHash("sha256").update(raw).digest("hex").slice(0, 40);
  return `${runId.slice(0, 150)}:${digest}`;
}

export function splitSseFrames(buffer: string) {
  const frames: string[] = [];
  let rest = buffer;
  while (true) {
    const match = /\r?\n\r?\n/.exec(rest);
    if (!match || match.index === undefined) break;
    frames.push(rest.slice(0, match.index));
    rest = rest.slice(match.index + match[0].length);
  }
  return { frames, rest };
}

export function parseSseEvent(frame: string): ParsedSseEvent | null {
  let name = "message";
  let id: string | undefined;
  const data: string[] = [];
  for (const rawLine of frame.split(/\r?\n/)) {
    if (!rawLine || rawLine.startsWith(":")) continue;
    const colon = rawLine.indexOf(":");
    const field = colon < 0 ? rawLine : rawLine.slice(0, colon);
    const value = colon < 0 ? "" : rawLine.slice(colon + 1).replace(/^ /, "");
    if (field === "event") name = value;
    else if (field === "id") id = resource(value);
    else if (field === "data") data.push(value);
  }
  if (name !== "tool.started" || data.length === 0) return null;
  try {
    const payload = JSON.parse(data.join("\n"));
    return payload && typeof payload === "object" && !Array.isArray(payload)
      ? { id, payload: payload as Record<string, unknown> }
      : null;
  } catch {
    return null;
  }
}

export function toSkillTelemetryEvent(
  parsed: ParsedSseEvent,
  runId: string,
  sequence: number
): SkillTelemetryEvent | undefined {
  const toolName = parsed.payload.tool ?? parsed.payload.tool_name;
  const preview = typeof parsed.payload.preview === "string"
    ? parsed.payload.preview.split(" \u2192 ", 1)[0]?.trim()
    : undefined;
  if (toolName !== "skill_view" || !preview || !SKILL_RE.test(preview)) return undefined;
  const sourceId = parsed.id ?? createHash("sha256")
    .update(`${sequence}\0${JSON.stringify(parsed.payload)}`)
    .digest("hex")
    .slice(0, 32);
  const timestamp = typeof parsed.payload.timestamp === "string" ? parsed.payload.timestamp : "";
  return {
    event_id: telemetryEventId(runId, sourceId),
    event_type: "skill.invoked",
    occurred_at: timestamp && !Number.isNaN(Date.parse(timestamp)) ? timestamp : new Date().toISOString(),
    run_id: runId,
    ...(resource(parsed.payload.session_id) ? { session_id: resource(parsed.payload.session_id) } : {}),
    skill_name: preview,
    payload: { tool: "skill_view" }
  };
}

export async function recordSkillTelemetry(
  context: HermesRequestContext,
  events: SkillTelemetryEvent[]
) {
  const url = process.env.SYNCODE_SKILL_TELEMETRY_URL?.trim();
  const key = process.env.SYNCODE_HERMES_PROVISION_KEY?.trim();
  if (!url || !key || events.length === 0) return;
  try {
    await fetch(url, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${key}`,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ user_id: context.userId, profile: context.profile, events: events.slice(0, 100) }),
      cache: "no-store",
      signal: AbortSignal.timeout(2_000)
    });
  } catch {
    // Usage accounting is best effort and must never interrupt an agent run.
  }
}
