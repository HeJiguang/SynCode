import {
  assertAgentRuntimeResourceId,
  agentRuntimeProxyErrorResponse,
  proxyAgentRuntimeJson,
  resolveAgentRuntimeRequestContext
} from "../../../../../../../lib/agent-runtime-server";

type RouteContext = { params: Promise<{ sessionId: string }> };

export const dynamic = "force-dynamic";

export async function GET(request: Request, { params }: RouteContext) {
  try {
    const { sessionId: rawSessionId } = await params;
    const sessionId = assertAgentRuntimeResourceId(rawSessionId, "会话 ID");
    const context = await resolveAgentRuntimeRequestContext();
    const query = new URL(request.url).search;
    return await proxyAgentRuntimeJson(
      context,
      `/v1/sessions/${encodeURIComponent(sessionId)}/messages${query}`
    );
  } catch (error) {
    return agentRuntimeProxyErrorResponse(error, "加载 AI 消息失败。");
  }
}
