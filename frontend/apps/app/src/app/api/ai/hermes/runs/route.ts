import {
  hermesProxyErrorResponse,
  proxyHermesJson,
  resolveHermesRequestContext
} from "../../../../../lib/hermes-server";

export async function POST(request: Request) {
  try {
    const context = await resolveHermesRequestContext({ provision: true });
    return await proxyHermesJson(context, "/v1/runs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: await request.text()
    });
  } catch (error) {
    return hermesProxyErrorResponse(error, "创建 Hermes 运行失败。");
  }
}
