import { hermesProxyErrorResponse, resolveHermesRequestContext } from "../../../../../../lib/hermes-server";
import { callSkillGovernance } from "../../../../../../lib/skill-governance-server";

const SKILL_RE = /^[a-z0-9][a-z0-9_-]{0,63}$/;

export async function POST(request: Request) {
  try {
    const context = await resolveHermesRequestContext({ provision: true });
    const body = await request.json() as { skill_name?: string; version?: string };
    const name = body.skill_name?.trim() ?? "";
    const version = body.version?.trim() ?? "";
    if (!SKILL_RE.test(name) || !/^\d+\.\d+\.\d+$/.test(version)) {
      return Response.json({ message: "Skill 回滚参数无效。" }, { status: 400 });
    }
    const payload = await callSkillGovernance(
      context,
      "/internal/skill-governance/users/rollback",
      {
        method: "POST",
        body: JSON.stringify({
          user_id: context.userId,
          profile: context.profile,
          skill_name: name,
          version
        })
      }
    );
    return Response.json(payload);
  } catch (error) {
    return hermesProxyErrorResponse(error, "回滚 Skill 失败。");
  }
}
