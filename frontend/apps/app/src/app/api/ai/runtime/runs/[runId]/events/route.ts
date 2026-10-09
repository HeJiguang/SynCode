import {
  assertAgentRuntimeResourceId,
  agentRuntimeHeaders,
  agentRuntimeProxyErrorResponse,
  agentRuntimeUrl,
  resolveAgentRuntimeRequestContext
} from "../../../../../../../lib/agent-runtime-server";

type RouteContext = { params: Promise<{ runId: string }> };

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET(request: Request, { params }: RouteContext) {
  try {
    const { runId: rawRunId } = await params;
    const runId = assertAgentRuntimeResourceId(rawRunId, "运行 ID");
    const context = await resolveAgentRuntimeRequestContext();
    const upstream = await fetch(agentRuntimeUrl(`/v1/runs/${encodeURIComponent(runId)}/events`), {
      headers: agentRuntimeHeaders(context),
      cache: "no-store",
      signal: request.signal
    });
    if (!upstream.ok || !upstream.body) {
      return new Response(await upstream.text(), {
        status: upstream.status,
        headers: { "Content-Type": upstream.headers.get("Content-Type") ?? "application/json" }
      });
    }
    return new Response(upstream.body, {
      status: upstream.status,
      headers: {
        "Content-Type": "text/event-stream; charset=utf-8",
        "Cache-Control": "no-cache, no-transform",
        Connection: "keep-alive",
        "X-Accel-Buffering": "no"
      }
    });
  } catch (error) {
    return agentRuntimeProxyErrorResponse(error, "连接 AI 事件流失败。");
  }
}
