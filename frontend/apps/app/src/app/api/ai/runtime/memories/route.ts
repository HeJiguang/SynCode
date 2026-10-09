import {
  agentRuntimeProxyErrorResponse,
  proxyAgentRuntimeJson,
  resolveAgentRuntimeRequestContext
} from "../../../../../lib/agent-runtime-server";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const context = await resolveAgentRuntimeRequestContext();
    return await proxyAgentRuntimeJson(context, "/v1/memories");
  } catch (error) {
    return agentRuntimeProxyErrorResponse(error, "读取长期记忆失败。");
  }
}
