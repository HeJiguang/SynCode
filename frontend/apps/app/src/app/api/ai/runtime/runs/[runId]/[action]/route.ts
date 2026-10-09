import {
  assertAgentRuntimeResourceId,
  agentRuntimeProxyErrorResponse,
  proxyAgentRuntimeJson,
  resolveAgentRuntimeRequestContext
} from "../../../../../../../lib/agent-runtime-server";

type RouteContext = { params: Promise<{ runId: string; action: string }> };

const ACTIONS = new Set(["approval", "steer", "stop"]);

export async function POST(request: Request, { params }: RouteContext) {
  try {
    const { runId: rawRunId, action } = await params;
    const runId = assertAgentRuntimeResourceId(rawRunId, "运行 ID");
    if (!ACTIONS.has(action)) {
      return Response.json({ message: "不支持的 AI 运行控制操作。" }, { status: 404 });
    }
    const context = await resolveAgentRuntimeRequestContext();
    return await proxyAgentRuntimeJson(context, `/v1/runs/${encodeURIComponent(runId)}/${action}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: await request.text() || "{}"
    });
  } catch (error) {
    return agentRuntimeProxyErrorResponse(error, "AI 运行控制操作失败。");
  }
}
