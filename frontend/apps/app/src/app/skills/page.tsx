import * as React from "react";
import { redirect } from "next/navigation";

import { AppShell } from "../../components/app-shell";
import { SkillsWorkspace } from "../../components/skills-workspace";
import { appInternalPath } from "../../lib/paths";
import { getServerAuthSession } from "../../lib/server-auth";

export default async function SkillsPage() {
  const { token, demoMode } = await getServerAuthSession();
  if (!token && !demoMode) redirect(appInternalPath("/login"));

  return (
    <AppShell demoMode={demoMode}>
      <div>
        <p className="kicker">Hermes</p>
        <h1 className="mt-2 text-3xl font-semibold text-[var(--text-primary)]">我的 Skills</h1>
      </div>
      <SkillsWorkspace />
    </AppShell>
  );
}
