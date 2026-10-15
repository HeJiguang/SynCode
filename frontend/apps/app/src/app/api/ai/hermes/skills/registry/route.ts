import { hermesProxyErrorResponse, resolveHermesRequestContext } from "../../../../../../lib/hermes-server";
import { callSkillGovernance } from "../../../../../../lib/skill-governance-server";

export async function GET() {
  try {
    const context = await resolveHermesRequestContext({ provision: true });
    const payload = await callSkillGovernance(
      context,
      `/internal/skill-governance/users/${encodeURIComponent(context.userId)}/skills`
    );
    return Response.json(payload);
  } catch (error) {
    return hermesProxyErrorResponse(error, "加载个人 Skill 版本失败。");
  }
}
