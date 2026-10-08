import {
  assertHermesResourceId,
  hermesProxyErrorResponse,
  proxyHermesJson,
  resolveHermesRequestContext
} from "../../../../../../lib/hermes-server";

type RouteContext = { params: Promise<{ sessionId: string }> };

export async function PATCH(request: Request, { params }: RouteContext) {
  try {
    const { sessionId: rawSessionId } = await params;
    const sessionId = assertHermesResourceId(rawSessionId, "会话 ID");
    const context = await resolveHermesRequestContext();
    const body = await request.text();
    return await proxyHermesJson(context, `/api/sessions/${encodeURIComponent(sessionId)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body
    });
  } catch (error) {
    return hermesProxyErrorResponse(error, "更新 Hermes 会话失败。");
  }
}
