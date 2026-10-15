import { hermesProxyErrorResponse, resolveHermesRequestContext } from "../../../../../../../lib/hermes-server";
import { callSkillGovernance } from "../../../../../../../lib/skill-governance-server";

type RouteContext = { params: Promise<{ skillName: string }> };
const SKILL_RE = /^[a-z0-9][a-z0-9_-]{0,63}$/;

export async function GET(_request: Request, context: RouteContext) {
  try {
    const hermes = await resolveHermesRequestContext({ provision: true });
    const { skillName } = await context.params;
    if (!SKILL_RE.test(skillName)) {
      return Response.json({ message: "Skill 名称格式无效。" }, { status: 400 });
    }
    const payload = await callSkillGovernance(
      hermes,
      `/internal/skill-governance/users/${encodeURIComponent(hermes.userId)}/skills/${encodeURIComponent(skillName)}/versions`
    );
    return Response.json(payload);
  } catch (error) {
    return hermesProxyErrorResponse(error, "加载 Skill 版本失败。");
  }
}
