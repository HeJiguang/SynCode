import {
  assertAgentRuntimeResourceId,
  agentRuntimeProxyErrorResponse,
  proxyAgentRuntimeJson,
  resolveAgentRuntimeRequestContext
} from "../../../../../../lib/agent-runtime-server";

type RouteContext = { params: Promise<{ sessionId: string }> };

export async function PATCH(request: Request, { params }: RouteContext) {
  try {
    const { sessionId: rawSessionId } = await params;
    const sessionId = assertAgentRuntimeResourceId(rawSessionId, "会话 ID");
    const context = await resolveAgentRuntimeRequestContext();
    return await proxyAgentRuntimeJson(context, `/v1/sessions/${encodeURIComponent(sessionId)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: await request.text()
    });
  } catch (error) {
    return agentRuntimeProxyErrorResponse(error, "更新 AI 会话失败。");
  }
}
