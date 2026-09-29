import { NextResponse } from "next/server";

import type { AiConversationSnapshot } from "@aioj/api";
import { requestJson } from "@aioj/api";

import { resolveAgentApiBaseUrl } from "../../../../../lib/agent-base-url";
import { resolveApiRouteError } from "../../../../../lib/api-route-error";
import { getServerAccessToken } from "../../../../../lib/server-auth";

type RouteProps = {
  params: Promise<{ conversationId: string }>;
};

export async function GET(_request: Request, { params }: RouteProps) {
  const token = await getServerAccessToken();
  if (!token) {
    return NextResponse.json({ message: "请先登录后查看 AI 对话。" }, { status: 401 });
  }

  try {
    const { conversationId } = await params;
    const payload = await requestJson<AiConversationSnapshot>(
      `/api/conversations/${encodeURIComponent(conversationId)}`,
      { token, baseUrl: resolveAgentApiBaseUrl() }
    );
    return NextResponse.json(payload);
  } catch (error) {
    const resolved = resolveApiRouteError(error, "加载 AI 对话失败。");
    return NextResponse.json(resolved.body, { status: resolved.status });
  }
}
