import { NextResponse } from "next/server";

import type { AiConversation, AiConversationSnapshot } from "@aioj/api";
import { requestJson } from "@aioj/api";

import { resolveAgentApiBaseUrl } from "../../../../lib/agent-base-url";
import { resolveApiRouteError } from "../../../../lib/api-route-error";
import { getServerAccessToken } from "../../../../lib/server-auth";

export async function GET() {
  const token = await getServerAccessToken();
  if (!token) {
    return NextResponse.json({ message: "请先登录后查看 AI 对话。" }, { status: 401 });
  }

  try {
    const payload = await requestJson<AiConversation[]>("/api/conversations", {
      token,
      baseUrl: resolveAgentApiBaseUrl()
    });
    return NextResponse.json(payload);
  } catch (error) {
    const resolved = resolveApiRouteError(error, "加载 AI 对话失败。");
    return NextResponse.json(resolved.body, { status: resolved.status });
  }
}

export async function POST(request: Request) {
  const token = await getServerAccessToken();
  if (!token) {
    return NextResponse.json({ message: "请先登录后创建 AI 对话。" }, { status: 401 });
  }

  try {
    const body = await request.json();
    const payload = await requestJson<AiConversationSnapshot>("/api/conversations", {
      method: "POST",
      token,
      baseUrl: resolveAgentApiBaseUrl(),
      body: JSON.stringify(body)
    });
    return NextResponse.json(payload);
  } catch (error) {
    const resolved = resolveApiRouteError(error, "创建 AI 对话失败。");
    return NextResponse.json(resolved.body, { status: resolved.status });
  }
}
