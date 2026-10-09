import {
  agentRuntimeProxyErrorResponse,
  proxyAgentRuntimeJson,
  resolveAgentRuntimeRequestContext
} from "../../../../../lib/agent-runtime-server";

export async function POST(request: Request) {
  try {
    const context = await resolveAgentRuntimeRequestContext();
    return await proxyAgentRuntimeJson(context, "/v1/runs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: await request.text()
    });
  } catch (error) {
    return agentRuntimeProxyErrorResponse(error, "创建 AI 运行失败。");
  }
}
