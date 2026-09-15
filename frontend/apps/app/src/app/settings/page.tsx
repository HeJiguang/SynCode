import * as React from "react";
import { getPublicMessages, getUserProfile } from "@aioj/api";
import { redirect } from "next/navigation";

import { AnnouncementCenter } from "../../components/announcement-center";
import { AppShell } from "../../components/app-shell";
import { ProfileSettingsForm } from "../../components/profile-settings-form";
import { appInternalPath } from "../../lib/paths";
import { getServerAuthSession } from "../../lib/server-auth";
import { Panel } from "@aioj/ui";

export default async function SettingsPage() {
  const { token, demoMode } = await getServerAuthSession();
  if (!token && !demoMode) {
    redirect(appInternalPath("/login"));
  }

  const [profile, messages] = await Promise.all([
    getUserProfile(token),
    getPublicMessages(token, { forceMock: demoMode })
  ]);

  return (
    <AppShell demoMode={demoMode} rail={<AnnouncementCenter messages={messages.slice(0, 3)} />}>
      <ProfileSettingsForm profile={profile} demoMode={demoMode} />

      <Panel className="p-5">
        <p className="kicker">账号</p>
        <h2 className="mt-2 text-xl font-semibold text-[var(--text-primary)]">资料与账号</h2>
      </Panel>
    </AppShell>
  );
}
