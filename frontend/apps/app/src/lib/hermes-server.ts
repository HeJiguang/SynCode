import { createHash } from "node:crypto";

import { requestJson, type ApiEnvelope, unwrapData } from "@aioj/api";

import { getServerAccessToken } from "./server-auth";

const PROFILE_RE = /^syncode-u[0-9]+$/;
const RESOURCE_ID_RE = /^[A-Za-z0-9._:-]{1,192}$/;

type BackendUserDetail = {
  userId?: string | number | null;
};

export class HermesProxyError extends Error {
  constructor(
    message: string,
    public status: number
  ) {
    super(message);
    this.name = "HermesProxyError";
  }
}

export type HermesRequestContext = {
  userId: string;
  profile: string;
  sessionKey: string;
};

function requiredEnv(name: string) {
  const value = process.env[name]?.trim();
  if (!value) {
    throw new HermesProxyError(`服务端缺少 ${name} 配置。`, 503);
  }
  return value;
}

export function hermesProfileForUser(userId: string) {
  if (!/^[0-9]+$/.test(userId)) {
    throw new HermesProxyError("当前用户身份格式无效。", 401);
  }
  return `syncode-u${userId}`;
}

export function assertHermesResourceId(value: string, kind: string) {
  if (!RESOURCE_ID_RE.test(value)) {
    throw new HermesProxyError(`${kind} 格式无效。`, 400);
  }
  return value;
}

async function resolveCurrentUserId() {
  const token = await getServerAccessToken();
  if (!token) {
    throw new HermesProxyError("请先登录后使用 AI 辅助。", 401);
  }
  const payload = await requestJson<ApiEnvelope<BackendUserDetail>>("/friend/user/detail", { token });
  const userId = String(unwrapData(payload).userId ?? "").trim();
  if (!/^[0-9]+$/.test(userId)) {
    throw new HermesProxyError("无法确认当前登录用户。", 401);
  }
  return userId;
}

async function ensureHermesProfile(context: HermesRequestContext) {
  const provisionUrl = process.env.SYNCODE_HERMES_PROVISION_URL?.trim();
  if (!provisionUrl) return;

  const provisionKey = requiredEnv("SYNCODE_HERMES_PROVISION_KEY");
  const response = await fetch(provisionUrl, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${provisionKey}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ user_id: context.userId, profile: context.profile }),
    cache: "no-store"
  });
  if (!response.ok) {
    throw new HermesProxyError("Hermes 用户运行环境初始化失败。", 503);
  }
}

export async function resolveHermesRequestContext(options: { provision?: boolean } = {}) {
  const userId = await resolveCurrentUserId();
  const profile = hermesProfileForUser(userId);
  const secret = requiredEnv("SYNCODE_HERMES_SESSION_SECRET");
  const sessionKey = `syncode-${createHash("sha256").update(`${secret}\0${userId}`).digest("hex").slice(0, 32)}`;
  const context = { userId, profile, sessionKey } satisfies HermesRequestContext;
  if (options.provision) await ensureHermesProfile(context);
  return context;
}

export function hermesUrl(context: HermesRequestContext, path: string) {
  if (!PROFILE_RE.test(context.profile) || !path.startsWith("/")) {
    throw new HermesProxyError("Hermes 请求路径无效。", 500);
  }
  const baseUrl = (process.env.SYNCODE_HERMES_BASE_URL ?? "http://127.0.0.1:8642").replace(/\/+$/, "");
  return `${baseUrl}/p/${context.profile}${path}`;
}

export function hermesHeaders(context: HermesRequestContext, init?: HeadersInit) {
  const headers = new Headers(init);
  headers.set("Authorization", `Bearer ${requiredEnv("SYNCODE_HERMES_API_KEY")}`);
  headers.set("X-Hermes-Session-Key", context.sessionKey);
  return headers;
}

export async function proxyHermesJson(
  context: HermesRequestContext,
  path: string,
  init: RequestInit = {}
) {
  const response = await fetch(hermesUrl(context, path), {
    ...init,
    headers: hermesHeaders(context, init.headers),
    cache: "no-store"
  });
  const text = await response.text();
  const headers = new Headers({ "Content-Type": response.headers.get("Content-Type") ?? "application/json" });
  return new Response(text, { status: response.status, headers });
}

export function hermesProxyErrorResponse(error: unknown, fallback: string) {
  const status = error instanceof HermesProxyError ? error.status : 502;
  const message = error instanceof Error ? error.message : fallback;
  return Response.json({ message }, { status });
}
