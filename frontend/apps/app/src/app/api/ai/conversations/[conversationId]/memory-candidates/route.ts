import { NextResponse } from "next/server";

import type { AiMemoryItem } from "@aioj/api";
import { requestJson } from "@aioj/api";

import { resolveAgentApiBaseUrl } from "../../../../../../lib/agent-base-url";
import { resolveApiRouteError } from "../../../../../../lib/api-route-error";
import { getServerAccessToken } from "../../../../../../lib/server-auth";

type RouteProps = {
  params: Promise<{ conversationId: string }>;
};

export async function GET(_request: Request, { params }: RouteProps) {
  const token = await getServerAccessToken();
  if (!token) {
    return NextResponse.json({ message: "请先登录后审核 AI 记忆。" }, { status: 401 });
  }

  try {
    const { conversationId } = await params;
    const payload = await requestJson<AiMemoryItem[]>(
      `/api/conversations/${encodeURIComponent(conversationId)}/memory-candidates`,
      { token, baseUrl: resolveAgentApiBaseUrl() }
    );
    return NextResponse.json(payload);
  } catch (error) {
    const resolved = resolveApiRouteError(error, "加载可继承记忆失败。");
    return NextResponse.json(resolved.body, { status: resolved.status });
  }
}
