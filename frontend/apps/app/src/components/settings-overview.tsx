import * as React from "react";
import type { UserProfile } from "@aioj/api";

import { Tag } from "@aioj/ui";

type SettingsOverviewProps = {
  profile: UserProfile;
};

export function SettingsOverview({ profile }: SettingsOverviewProps) {
  return (
    <div className="rounded-[var(--radius-card)] border border-[var(--border-soft)] bg-[var(--surface-1)]">
      {/* Header */}
      <div className="border-b border-[var(--border-soft)] px-5 py-4">
        <p className="kicker">Preferences</p>
        <h3 className="mt-0.5 text-base font-semibold text-[var(--text-primary)]">个人设置</h3>
      </div>

      {/* Settings Grid */}
      <div className="grid gap-px bg-[var(--border-soft)] md:grid-cols-2">
        {[
          { label: "默认语言", value: profile.preferredLanguage },
          { label: "编辑器主题", value: profile.editorTheme },
          { label: "时区", value: profile.timezone },
          {
            label: "邮箱提醒",
            value: profile.notifyByEmail ? "已开启" : "已关闭"
          }
        ].map((item) => (
          <div key={item.label} className="bg-[var(--surface-1)] px-5 py-4">
            <p className="text-xs text-[var(--text-muted)]">{item.label}</p>
            <p className="mt-1.5 text-sm font-semibold text-[var(--text-primary)]">{item.value}</p>
          </div>
        ))}
      </div>

      {/* Shortcuts */}
      <div className="border-t border-[var(--border-soft)] px-5 py-4">
        <p className="text-xs text-[var(--text-muted)]">快捷键偏好</p>
        <div className="mt-3 flex flex-wrap gap-1.5">
          {profile.shortcuts.map((item) => (
            <Tag key={item}>{item}</Tag>
          ))}
        </div>
      </div>
    </div>
  );
}
