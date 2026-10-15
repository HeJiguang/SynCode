import type { HermesRequestContext } from "./hermes-server";

function governanceEndpoint(path: string) {
  const base = process.env.SYNCODE_SKILL_GOVERNANCE_URL?.trim()
    ?? process.env.SYNCODE_HERMES_PROVISION_URL?.trim()?.replace(/\/internal\/profiles\/ensure$/, "");
  if (!base) throw new Error("Skill 治理服务尚未配置。");
  return `${base.replace(/\/+$/, "")}${path}`;
}

function governanceKey() {
  const key = process.env.SYNCODE_HERMES_PROVISION_KEY?.trim();
  if (!key) throw new Error("Skill 治理凭据尚未配置。");
  return key;
}

export async function callSkillGovernance(
  context: HermesRequestContext,
  path: string,
  init: RequestInit = {}
) {
  const headers = new Headers(init.headers);
  headers.set("Authorization", `Bearer ${governanceKey()}`);
  if (init.body) headers.set("Content-Type", "application/json");
  const response = await fetch(governanceEndpoint(path), {
    ...init,
    headers,
    cache: "no-store"
  });
  const payload = await response.json().catch(() => ({ detail: "Skill 治理服务返回了无效响应。" }));
  if (!response.ok) {
    throw new Error(typeof payload.detail === "string" ? payload.detail : "Skill 治理操作失败。");
  }
  return payload;
}

export async function syncPersonalSkills(context: HermesRequestContext) {
  return callSkillGovernance(context, "/internal/skill-governance/users/sync", {
    method: "POST",
    body: JSON.stringify({ user_id: context.userId, profile: context.profile })
  });
}
