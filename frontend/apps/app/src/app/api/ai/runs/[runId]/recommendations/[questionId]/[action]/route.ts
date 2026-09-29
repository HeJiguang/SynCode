import { NextResponse } from "next/server";

import { requestJson } from "@aioj/api";

import { resolveAgentApiBaseUrl } from "../../../../../../../../lib/agent-base-url";
import { resolveApiRouteError } from "../../../../../../../../lib/api-route-error";
import { getServerAccessToken } from "../../../../../../../../lib/server-auth";

type RouteContext = {
  params: Promise<{ runId: string; questionId: string; action: string }>;
};

export async function POST(_request: Request, { params }: RouteContext) {
  const token = await getServerAccessToken();
  if (!token) return NextResponse.json({ message: "请先登录。" }, { status: 401 });
  const { runId, questionId, action } = await params;
  if (!/^run_[a-f0-9]+$/.test(runId) || !/^\d+$/.test(questionId) || !["impression", "click"].includes(action)) {
    return NextResponse.json({ message: "推荐事件无效。" }, { status: 400 });
  }
  try {
    const result = await requestJson<{ recorded: boolean }>(
      `/api/runs/${runId}/recommendations/${questionId}/${action}`,
      { method: "POST", token, baseUrl: resolveAgentApiBaseUrl() }
    );
    return NextResponse.json(result);
  } catch (error) {
    const resolved = resolveApiRouteError(error, "记录推荐事件失败。");
    return NextResponse.json(resolved.body, { status: resolved.status });
  }
}
