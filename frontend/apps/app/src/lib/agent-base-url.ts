export const DEFAULT_AGENT_API_BASE_URL = "http://127.0.0.1:8016";

export function resolveAgentApiBaseUrl() {
  const baseUrl =
    process.env.AGENT_PUBLIC_BASE_URL ??
    process.env.SYNCODE_AGENT_BASE_URL ??
    DEFAULT_AGENT_API_BASE_URL;

  return baseUrl.replace(/\/+$/, "");
}
