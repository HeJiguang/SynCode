import { NextResponse } from "next/server";

import type { AiToolApproval } from "@aioj/api";
import { requestJson } from "@aioj/api";

import { resolveAgentApiBaseUrl } from "../../../../../../lib/agent-base-url";
import { resolveApiRouteError } from "../../../../../../lib/api-route-error";
import { getServerAccessToken } from "../../../../../../lib/server-auth";

type RouteProps = {
  params: Promise<{ approvalId: string; action: string }>;
};

export async function POST(_request: Request, { params }: RouteProps) {
  const token = await getServerAccessToken();
  if (!token) {
    return NextResponse.json({ message: "请先登录后处理工具审批。" }, { status: 401 });
  }

  try {
    const { approvalId, action } = await params;
    if (action !== "approve" && action !== "deny") {
      return NextResponse.json({ message: "不支持的审批操作。" }, { status: 400 });
    }
    const payload = await requestJson<AiToolApproval>(
      `/api/tool-approvals/${encodeURIComponent(approvalId)}/${action}`,
      { method: "POST", token, baseUrl: resolveAgentApiBaseUrl() }
    );
    return NextResponse.json(payload);
  } catch (error) {
    const resolved = resolveApiRouteError(error, "处理工具审批失败。");
    return NextResponse.json(resolved.body, { status: resolved.status });
  }
}
