import {
  hermesProxyErrorResponse,
  proxyHermesJson,
  resolveHermesRequestContext
} from "../../../../../../lib/hermes-server";
import {
  callSkillGovernance,
  syncPersonalSkills
} from "../../../../../../lib/skill-governance-server";

const SKILL_RE = /^[a-z0-9][a-z0-9_-]{0,63}$/;

async function isPersonalSkill(context: Awaited<ReturnType<typeof resolveHermesRequestContext>>, name: string) {
  const rows = await callSkillGovernance(
    context,
    `/internal/skill-governance/users/${encodeURIComponent(context.userId)}/skills`
  ) as Array<{ skill_name?: string; lifecycle_status?: string }>;
  return rows.some((row) => row.skill_name === name && row.lifecycle_status === "active");
}

export async function GET(request: Request) {
  try {
    const context = await resolveHermesRequestContext({ provision: true });
    const name = new URL(request.url).searchParams.get("name")?.trim() ?? "";
    if (!SKILL_RE.test(name)) return Response.json({ message: "Skill 名称格式无效。" }, { status: 400 });
    return await proxyHermesJson(context, `/api/skills/content?name=${encodeURIComponent(name)}`);
  } catch (error) {
    return hermesProxyErrorResponse(error, "加载 Skill 内容失败。");
  }
}

export async function PUT(request: Request) {
  try {
    const context = await resolveHermesRequestContext({ provision: true });
    const body = await request.json() as { name?: string; content?: string };
    const name = body.name?.trim() ?? "";
    if (!SKILL_RE.test(name) || typeof body.content !== "string") {
      return Response.json({ message: "Skill 修改内容无效。" }, { status: 400 });
    }
    if (!await isPersonalSkill(context, name)) {
      return Response.json({ message: "平台 Skill 只能由管理员发布，用户不能直接修改。" }, { status: 403 });
    }
    const response = await proxyHermesJson(context, "/api/skills/content", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, content: body.content })
    });
    if (response.ok) await syncPersonalSkills(context);
    return response;
  } catch (error) {
    return hermesProxyErrorResponse(error, "修改 Skill 失败。");
  }
}
