import {
  assertHermesResourceId,
  hermesProxyErrorResponse,
  proxyHermesJson,
  resolveHermesRequestContext
} from "../../../../../../../lib/hermes-server";

type RouteContext = { params: Promise<{ runId: string; action: string }> };

const ACTIONS = new Set(["approval", "steer", "stop"]);

export async function POST(request: Request, { params }: RouteContext) {
  try {
    const { runId: rawRunId, action } = await params;
    const runId = assertHermesResourceId(rawRunId, "运行 ID");
    if (!ACTIONS.has(action)) {
      return Response.json({ message: "不支持的 Hermes 控制操作。" }, { status: 404 });
    }
    const context = await resolveHermesRequestContext();
    const body = await request.text();
    return await proxyHermesJson(context, `/v1/runs/${encodeURIComponent(runId)}/${action}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: body || "{}"
    });
  } catch (error) {
    return hermesProxyErrorResponse(error, "Hermes 控制操作失败。");
  }
}
