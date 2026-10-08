import {
  hermesProxyErrorResponse,
  proxyHermesJson,
  resolveHermesRequestContext
} from "../../../../../lib/hermes-server";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  try {
    const context = await resolveHermesRequestContext({ provision: true });
    const query = new URL(request.url).search;
    return await proxyHermesJson(context, `/api/sessions${query}`);
  } catch (error) {
    return hermesProxyErrorResponse(error, "加载 Hermes 会话失败。");
  }
}

export async function POST(request: Request) {
  try {
    const context = await resolveHermesRequestContext({ provision: true });
    const body = await request.text();
    return await proxyHermesJson(context, "/api/sessions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body
    });
  } catch (error) {
    return hermesProxyErrorResponse(error, "创建 Hermes 会话失败。");
  }
}
