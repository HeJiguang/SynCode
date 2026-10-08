import {
  assertHermesResourceId,
  hermesProxyErrorResponse,
  proxyHermesJson,
  resolveHermesRequestContext
} from "../../../../../../../lib/hermes-server";

type RouteContext = { params: Promise<{ sessionId: string }> };

export const dynamic = "force-dynamic";

export async function GET(request: Request, { params }: RouteContext) {
  try {
    const { sessionId: rawSessionId } = await params;
    const sessionId = assertHermesResourceId(rawSessionId, "会话 ID");
    const context = await resolveHermesRequestContext();
    const query = new URL(request.url).search;
    return await proxyHermesJson(
      context,
      `/api/sessions/${encodeURIComponent(sessionId)}/messages${query}`
    );
  } catch (error) {
    return hermesProxyErrorResponse(error, "加载 Hermes 消息失败。");
  }
}
