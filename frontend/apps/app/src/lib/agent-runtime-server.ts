import { createHash } from "node:crypto";

import { requestJson, type ApiEnvelope, unwrapData } from "@aioj/api";

import { getServerAccessToken } from "./server-auth";

const PUBLIC_RESOURCE_ID_RE = /^rt[rsmc]\.[a-z][a-z0-9-]{0,31}\.[A-Za-z0-9_-]+$/;

type BackendUserDetail = {
  userId?: string | number | null;
};

export class AgentRuntimeProxyError extends Error {
  constructor(
    message: string,
    public status: number
  ) {
    super(message);
    this.name = "AgentRuntimeProxyError";
  }
}

export type AgentRuntimeRequestContext = {
  userId: string;
  sessionKey: string;
};

function requiredEnv(name: string) {
  const value = process.env[name]?.trim();
  if (!value) {
    throw new AgentRuntimeProxyError(`服务端缺少 ${name} 配置。`, 503);
  }
  return value;
}

export function assertAgentRuntimeResourceId(value: string, kind: string) {
  if (!PUBLIC_RESOURCE_ID_RE.test(value) || value.length > 8192) {
    throw new AgentRuntimeProxyError(`${kind} 格式无效。`, 400);
  }
  return value;
}

async function resolveCurrentUserId() {
  const token = await getServerAccessToken();
  if (!token) {
    throw new AgentRuntimeProxyError("请先登录后使用 AI 辅助。", 401);
  }
  const payload = await requestJson<ApiEnvelope<BackendUserDetail>>("/friend/user/detail", { token });
  const userId = String(unwrapData(payload).userId ?? "").trim();
  if (!/^[0-9]+$/.test(userId)) {
    throw new AgentRuntimeProxyError("无法确认当前登录用户。", 401);
  }
  return userId;
}

export async function resolveAgentRuntimeRequestContext() {
  const userId = await resolveCurrentUserId();
  const secret = requiredEnv("SYNCODE_AGENT_RUNTIME_SESSION_SECRET");
  const sessionKey = `syncode-${createHash("sha256").update(`${secret}\0${userId}`).digest("hex").slice(0, 32)}`;
  return { userId, sessionKey } satisfies AgentRuntimeRequestContext;
}

export function agentRuntimeUrl(path: string) {
  if (!path.startsWith("/v1/")) {
    throw new AgentRuntimeProxyError("Agent Runtime 请求路径无效。", 500);
  }
  const baseUrl = (process.env.SYNCODE_AGENT_RUNTIME_BASE_URL ?? "http://127.0.0.1:8017").replace(/\/+$/, "");
  return `${baseUrl}${path}`;
}

export function agentRuntimeHeaders(context: AgentRuntimeRequestContext, init?: HeadersInit) {
  const headers = new Headers(init);
  headers.set("Authorization", `Bearer ${requiredEnv("SYNCODE_AGENT_RUNTIME_API_KEY")}`);
  headers.set("X-SynCode-User-ID", context.userId);
  headers.set("X-SynCode-Session-Key", context.sessionKey);
  return headers;
}

export async function proxyAgentRuntimeJson(
  context: AgentRuntimeRequestContext,
  path: string,
  init: RequestInit = {}
) {
  const response = await fetch(agentRuntimeUrl(path), {
    ...init,
    headers: agentRuntimeHeaders(context, init.headers),
    cache: "no-store"
  });
  const text = await response.text();
  const headers = new Headers({ "Content-Type": response.headers.get("Content-Type") ?? "application/json" });
  return new Response(text, { status: response.status, headers });
}

export function agentRuntimeProxyErrorResponse(error: unknown, fallback: string) {
  const status = error instanceof AgentRuntimeProxyError ? error.status : 502;
  const message = error instanceof Error ? error.message : fallback;
  return Response.json({ message }, { status });
}
