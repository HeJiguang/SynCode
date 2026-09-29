import { NextResponse } from "next/server";

import { requestJson } from "@aioj/api";

import { resolveAgentApiBaseUrl } from "../../../../../lib/agent-base-url";
import { resolveApiRouteError } from "../../../../../lib/api-route-error";
import { getServerAccessToken } from "../../../../../lib/server-auth";

type RouteProps = {
  params: Promise<{ runId: string }>;
};

export async function GET(_request: Request, { params }: RouteProps) {
  const token = await getServerAccessToken();
  if (!token) {
    return NextResponse.json({ message: "请先登录后查看 AI 运行状态。" }, { status: 401 });
  }

  try {
    const { runId } = await params;
    const payload = await requestJson<Record<string, unknown>>(
      `/api/runs/${encodeURIComponent(runId)}`,
      { token, baseUrl: resolveAgentApiBaseUrl() }
    );
    return NextResponse.json(payload);
  } catch (error) {
    const resolved = resolveApiRouteError(error, "加载 AI 运行状态失败。");
    return NextResponse.json(resolved.body, { status: resolved.status });
  }
}
