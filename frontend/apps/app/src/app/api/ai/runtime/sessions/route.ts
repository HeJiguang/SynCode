import {
  agentRuntimeProxyErrorResponse,
  proxyAgentRuntimeJson,
  resolveAgentRuntimeRequestContext
} from "../../../../../lib/agent-runtime-server";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  try {
    const context = await resolveAgentRuntimeRequestContext();
    const query = new URL(request.url).search;
    return await proxyAgentRuntimeJson(context, `/v1/sessions${query}`);
  } catch (error) {
    return agentRuntimeProxyErrorResponse(error, "加载 AI 会话失败。");
  }
}

export async function POST(request: Request) {
  try {
    const context = await resolveAgentRuntimeRequestContext();
    return await proxyAgentRuntimeJson(context, "/v1/sessions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: await request.text()
    });
  } catch (error) {
    return agentRuntimeProxyErrorResponse(error, "创建 AI 会话失败。");
  }
}
