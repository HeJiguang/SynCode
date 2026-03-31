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
        <h2 className="mt-2 text-xl font-semibold text-[var(--text-primary)]">生产环境接入说明</h2>
        <div className="mt-4 space-y-3 text-sm leading-7 text-[var(--text-secondary)]">
          <p>头像通过现有 `/friend/file/upload` 上传到 OSS，再回写到用户资料。</p>
          <p>昵称、邮箱、学校、专业和个人简介会直接写入真实用户信息，不再使用演示态资料。</p>
          <p>如果后端接口异常，设置页不会再静默回退 demo 数据，而是直接显示保存失败。</p>
        </div>
      </Panel>
    </AppShell>
  );
}
