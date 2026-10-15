import {
  hermesProxyErrorResponse,
  proxyHermesJson,
  resolveHermesRequestContext
} from "../../../../../lib/hermes-server";
import { syncPersonalSkills } from "../../../../../lib/skill-governance-server";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const context = await resolveHermesRequestContext({ provision: true });
    return await proxyHermesJson(context, "/api/skills");
  } catch (error) {
    return hermesProxyErrorResponse(error, "加载 Skill 失败。");
  }
}

export async function POST(request: Request) {
  try {
    const context = await resolveHermesRequestContext({ provision: true });
    const body = await request.text();
    const response = await proxyHermesJson(context, "/api/skills", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body
    });
    if (response.ok) await syncPersonalSkills(context);
    return response;
  } catch (error) {
    return hermesProxyErrorResponse(error, "创建 Skill 失败。");
  }
}
