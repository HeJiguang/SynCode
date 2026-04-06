import * as React from "react";
import { getPublicMessages, getUserProfile } from "@aioj/api";
import { frontendPreviewMode } from "@aioj/config";
import { redirect } from "next/navigation";

import { AnnouncementCenter } from "../../components/announcement-center";
import { AppShell } from "../../components/app-shell";
import { ProfileSettingsForm } from "../../components/profile-settings-form";
import { appInternalPath } from "../../lib/paths";
import { getServerAccessToken } from "../../lib/server-auth";
import { Panel } from "@aioj/ui";

export default async function SettingsPage() {
  const token = await getServerAccessToken();
  if (!token && !frontendPreviewMode) {
    redirect(appInternalPath("/login"));
  }

  const [profile, messages] = await Promise.all([getUserProfile(token), getPublicMessages(token)]);

  return (
    <AppShell rail={<AnnouncementCenter messages={messages.slice(0, 3)} />}>
      <ProfileSettingsForm profile={profile} />

      <Panel className="p-5">
        <p className="kicker">账号</p>
        <h2 className="mt-2 text-xl font-semibold text-[var(--text-primary)]">资料与账号</h2>
      </Panel>
    </AppShell>
  );
}
