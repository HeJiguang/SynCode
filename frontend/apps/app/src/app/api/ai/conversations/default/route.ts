import { NextResponse } from "next/server";

import type { AiConversationSnapshot } from "@aioj/api";
import { requestJson } from "@aioj/api";

import { resolveAgentApiBaseUrl } from "../../../../../lib/agent-base-url";
import { resolveApiRouteError } from "../../../../../lib/api-route-error";
import { getServerAccessToken } from "../../../../../lib/server-auth";

export async function GET() {
  const token = await getServerAccessToken();
  if (!token) {
    return NextResponse.json({ message: "请先登录后使用 AI 助手。" }, { status: 401 });
  }

  try {
    const payload = await requestJson<AiConversationSnapshot>("/api/conversations/default", {
      token,
      baseUrl: resolveAgentApiBaseUrl()
    });
    return NextResponse.json(payload);
  } catch (error) {
    const resolved = resolveApiRouteError(error, "加载默认 AI 对话失败。");
    return NextResponse.json(resolved.body, { status: resolved.status });
  }
}
