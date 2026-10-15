import { hermesProxyErrorResponse, resolveHermesRequestContext } from "../../../../../../lib/hermes-server";
import { callSkillGovernance } from "../../../../../../lib/skill-governance-server";

const SKILL_RE = /^[a-z0-9][a-z0-9_-]{0,63}$/;

export async function POST(request: Request) {
  try {
    const context = await resolveHermesRequestContext({ provision: true });
    const body = await request.json() as { action?: "archive" | "restore"; skill_name?: string };
    const name = body.skill_name?.trim() ?? "";
    if (!SKILL_RE.test(name) || !["archive", "restore"].includes(body.action ?? "")) {
      return Response.json({ message: "Skill 生命周期操作无效。" }, { status: 400 });
    }
    const payload = await callSkillGovernance(
      context,
      `/internal/skill-governance/users/${body.action}`,
      {
        method: "POST",
        body: JSON.stringify({ user_id: context.userId, profile: context.profile, skill_name: name })
      }
    );
    return Response.json(payload);
  } catch (error) {
    return hermesProxyErrorResponse(error, "更新 Skill 状态失败。");
  }
}
