import {
  assertAgentRuntimeResourceId,
  agentRuntimeProxyErrorResponse,
  proxyAgentRuntimeJson,
  resolveAgentRuntimeRequestContext
} from "../../../../../../../lib/agent-runtime-server";

type RouteContext = { params: Promise<{ candidateId: string; action: string }> };

const ACTIONS = new Set(["approve", "reject"]);

export async function POST(request: Request, { params }: RouteContext) {
  try {
    const { candidateId: rawCandidateId, action } = await params;
    const candidateId = assertAgentRuntimeResourceId(rawCandidateId, "上下文候选 ID");
    if (!ACTIONS.has(action)) {
      return Response.json({ message: "不支持的上下文审核操作。" }, { status: 404 });
    }
    const body = await request.text();
    if (body.length > 24_000) {
      return Response.json({ message: "上下文摘要修改过长。" }, { status: 413 });
    }
    const context = await resolveAgentRuntimeRequestContext();
    return await proxyAgentRuntimeJson(
      context,
      `/v1/context-candidates/${encodeURIComponent(candidateId)}/${action}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: body || "{}"
      }
    );
  } catch (error) {
    return agentRuntimeProxyErrorResponse(error, "上下文摘要审核失败。");
  }
}
