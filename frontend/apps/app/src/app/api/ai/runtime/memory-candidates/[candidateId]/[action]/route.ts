import {
  assertAgentRuntimeResourceId,
  agentRuntimeProxyErrorResponse,
  proxyAgentRuntimeJson,
  resolveAgentRuntimeRequestContext
} from "../../../../../../../lib/agent-runtime-server";

type RouteContext = { params: Promise<{ candidateId: string; action: string }> };

const ACTIONS = new Set(["approve", "reject"]);

export async function POST(_request: Request, { params }: RouteContext) {
  try {
    const { candidateId: rawCandidateId, action } = await params;
    const candidateId = assertAgentRuntimeResourceId(rawCandidateId, "记忆候选 ID");
    if (!ACTIONS.has(action)) {
      return Response.json({ message: "不支持的记忆审核操作。" }, { status: 404 });
    }
    const context = await resolveAgentRuntimeRequestContext();
    return await proxyAgentRuntimeJson(
      context,
      `/v1/memory-candidates/${encodeURIComponent(candidateId)}/${action}`,
      { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" }
    );
  } catch (error) {
    return agentRuntimeProxyErrorResponse(error, "记忆审核失败。");
  }
}
