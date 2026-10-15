import {
  hermesProxyErrorResponse,
  proxyHermesJson,
  resolveHermesRequestContext
} from "../../../../../lib/hermes-server";
import {
  enforceHermesRunRateLimit,
  parseHermesRunRequest
} from "../../../../../lib/hermes-run-contract";

export async function POST(request: Request) {
  try {
    const context = await resolveHermesRequestContext({ provision: true });
    enforceHermesRunRateLimit(context.userId);
    const body = await parseHermesRunRequest(request);
    return await proxyHermesJson(context, "/v1/runs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    });
  } catch (error) {
    return hermesProxyErrorResponse(error, "创建 Hermes 运行失败。");
  }
}
