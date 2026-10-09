import {
  assertAgentRuntimeResourceId,
  agentRuntimeProxyErrorResponse,
  proxyAgentRuntimeJson,
  resolveAgentRuntimeRequestContext
} from "../../../../../../../lib/agent-runtime-server";

type RouteContext = { params: Promise<{ runId: string }> };

export const dynamic = "force-dynamic";

export async function GET(_request: Request, { params }: RouteContext) {
  try {
    const { runId: rawRunId } = await params;
    const runId = assertAgentRuntimeResourceId(rawRunId, "运行 ID");
    const context = await resolveAgentRuntimeRequestContext();
    return await proxyAgentRuntimeJson(context, `/v1/runs/${encodeURIComponent(runId)}/artifacts`);
  } catch (error) {
    return agentRuntimeProxyErrorResponse(error, "读取 AI 运行产物失败。");
  }
}
