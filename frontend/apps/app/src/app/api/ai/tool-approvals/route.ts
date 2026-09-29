import { NextResponse } from "next/server";

import type { AiToolApproval } from "@aioj/api";
import { requestJson } from "@aioj/api";

import { resolveAgentApiBaseUrl } from "../../../../lib/agent-base-url";
import { resolveApiRouteError } from "../../../../lib/api-route-error";
import { getServerAccessToken } from "../../../../lib/server-auth";

export async function GET(request: Request) {
  const token = await getServerAccessToken();
  if (!token) {
    return NextResponse.json({ message: "请先登录后查看工具审批。" }, { status: 401 });
  }

  try {
    const incoming = new URL(request.url).searchParams;
    const query = new URLSearchParams();
    for (const key of ["runId", "conversationId"]) {
      const value = incoming.get(key);
      if (value) query.set(key, value);
    }
    const suffix = query.size ? `?${query.toString()}` : "";
    const payload = await requestJson<AiToolApproval[]>(`/api/tool-approvals${suffix}`, {
      token,
      baseUrl: resolveAgentApiBaseUrl()
    });
    return NextResponse.json(payload);
  } catch (error) {
    const resolved = resolveApiRouteError(error, "加载工具审批失败。");
    return NextResponse.json(resolved.body, { status: resolved.status });
  }
}
