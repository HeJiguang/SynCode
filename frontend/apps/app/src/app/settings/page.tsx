import * as React from "react";
import { getPublicMessages, getUserProfile } from "@aioj/api";
import { redirect } from "next/navigation";

import { AnnouncementCenter } from "../../components/announcement-center";
import { AppShell } from "../../components/app-shell";
import { ProfileSettingsForm } from "../../components/profile-settings-form";
import { appInternalPath } from "../../lib/paths";
import { getServerAccessToken } from "../../lib/server-auth";
import { Panel } from "@aioj/ui";

export default async function SettingsPage() {
  const token = await getServerAccessToken();
  if (!token) {
    redirect(appInternalPath("/login"));
  }

  const [profile, messages] = await Promise.all([getUserProfile(token), getPublicMessages(token)]);

  return (
    <AppShell rail={<AnnouncementCenter messages={messages.slice(0, 3)} />}>
      <ProfileSettingsForm profile={profile} />

      <Panel className="p-5">
        <p className="kicker">Account</p>
        <h2 className="mt-2 text-xl font-semibold text-[var(--text-primary)]">资料与账号</h2>
        <div className="mt-4 space-y-3 text-sm leading-7 text-[var(--text-secondary)]">
          <p>在这里更新头像、昵称、学校、专业和个人简介，系统会直接同步到你的账号资料。</p>
          <p>头像沿用现有文件上传链路保存，其余字段会在提交后立即写回个人信息。</p>
          <p>如果保存没有成功，页面会直接提示失败原因，方便你及时重试。</p>
        </div>
      </Panel>
    </AppShell>
  );
}
