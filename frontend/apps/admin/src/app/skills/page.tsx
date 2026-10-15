import * as React from "react";

import { AdminShell } from "../../components/admin-shell";
import { SkillGovernanceConsole } from "../../components/skill-governance-console";
import { getAdminProfile } from "../../lib/admin-api";
import { getOpenPromotionCandidates, getPendingLifecycleReviews } from "../../lib/skill-governance";
import { requireAdminAccessToken } from "../../lib/server-auth";

export default async function AdminSkillsPage() {
  const token = await requireAdminAccessToken();
  const [admin, candidates, lifecycleReviews] = await Promise.all([
    getAdminProfile(token),
    token ? getOpenPromotionCandidates() : Promise.resolve([]),
    token ? getPendingLifecycleReviews() : Promise.resolve([])
  ]);

  return (
    <AdminShell
      adminName={admin.nickName}
      title="Skill 治理"
      description="审查跨用户重复形成的能力，将脱敏后的公共经验发布为平台 Skill，并处理长期低使用版本。"
    >
      <SkillGovernanceConsole
        initialCandidates={candidates}
        initialLifecycleReviews={lifecycleReviews}
      />
    </AdminShell>
  );
}
