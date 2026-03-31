"use client";

import * as React from "react";
import { useMemo, useState, useTransition } from "react";
import type { UserProfile } from "@aioj/api";
import { Camera, LoaderCircle } from "lucide-react";

import { appApiPath } from "../lib/paths";
import { Button, Input, Panel, Textarea } from "@aioj/ui";

type ProfileSettingsFormProps = {
  profile: UserProfile;
};

export function ProfileSettingsForm({ profile }: ProfileSettingsFormProps) {
  const [form, setForm] = useState({
    nickName: profile.nickName,
    email: profile.email,
    schoolName: profile.schoolName,
    majorName: profile.majorName,
    introduce: profile.headline
  });
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, startSaving] = useTransition();
  const [isUploading, startUploading] = useTransition();
  const [avatarVersion, setAvatarVersion] = useState(0);

  const avatarUrl = useMemo(() => {
    if (!profile.headImage) return null;
    const separator = profile.headImage.includes("?") ? "&" : "?";
    return `${profile.headImage}${separator}v=${avatarVersion}`;
  }, [avatarVersion, profile.headImage]);

  const initial = (form.nickName || profile.email || "S").slice(0, 1).toUpperCase();

  function updateField(key: keyof typeof form, value: string) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage(null);
    setError(null);

    startSaving(async () => {
      const response = await fetch(appApiPath("/user/profile"), {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form)
      });

      if (!response.ok) {
        const payload = (await response.json().catch(() => null)) as { message?: string } | null;
        setError(payload?.message ?? "资料保存失败，请稍后重试。");
        return;
      }

      setMessage("资料已保存，页面即将刷新。");
      window.location.reload();
    });
  }

  function handleAvatarChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;

    setMessage(null);
    setError(null);
    startUploading(async () => {
      const formData = new FormData();
      formData.append("file", file);
      const response = await fetch(appApiPath("/user/avatar"), {
        method: "POST",
        body: formData
      });

      if (!response.ok) {
        const payload = (await response.json().catch(() => null)) as { message?: string } | null;
        setError(payload?.message ?? "头像上传失败，请稍后重试。");
        return;
      }

      setMessage("头像已更新，页面即将刷新。");
      setAvatarVersion((current) => current + 1);
      window.location.reload();
    });
  }

  return (
    <Panel className="p-6">
      <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
        <div className="flex items-center gap-4">
          <div className="flex h-20 w-20 items-center justify-center overflow-hidden rounded-[24px] border border-[var(--border-soft)] bg-[var(--surface-2)] text-2xl font-semibold text-[var(--text-primary)]">
            {avatarUrl ? <img src={avatarUrl} alt={form.nickName || "avatar"} className="h-full w-full object-cover" /> : initial}
          </div>
          <div className="space-y-2">
            <div>
              <p className="kicker">Profile</p>
              <h3 className="mt-1 text-xl font-semibold text-[var(--text-primary)]">个人资料</h3>
            </div>
            <label className="inline-flex cursor-pointer items-center gap-2 rounded-[14px] border border-[var(--border-soft)] bg-[var(--surface-2)] px-3 py-2 text-sm text-[var(--text-primary)] transition hover:border-[var(--border-strong)]">
              {isUploading ? <LoaderCircle size={14} className="animate-spin" /> : <Camera size={14} />}
              上传头像
              <input type="file" accept="image/*" className="hidden" onChange={handleAvatarChange} />
            </label>
          </div>
        </div>

        <div className="grid min-w-[220px] gap-3 sm:grid-cols-3 lg:grid-cols-1">
          <div className="rounded-[18px] border border-[var(--border-soft)] bg-[var(--surface-2)] px-4 py-3">
            <p className="text-xs text-[var(--text-muted)]">已解题数</p>
            <p className="mt-2 text-2xl font-semibold text-[var(--text-primary)]">{profile.solvedCount}</p>
          </div>
          <div className="rounded-[18px] border border-[var(--border-soft)] bg-[var(--surface-2)] px-4 py-3">
            <p className="text-xs text-[var(--text-muted)]">提交总数</p>
            <p className="mt-2 text-2xl font-semibold text-[var(--text-primary)]">{profile.submissionCount}</p>
          </div>
          <div className="rounded-[18px] border border-[var(--border-soft)] bg-[var(--surface-2)] px-4 py-3">
            <p className="text-xs text-[var(--text-muted)]">连续学习</p>
            <p className="mt-2 text-2xl font-semibold text-[var(--text-primary)]">{profile.streakDays} 天</p>
          </div>
        </div>
      </div>

      <form className="mt-6 space-y-5" onSubmit={handleSubmit}>
        <div className="grid gap-4 md:grid-cols-2">
          <label className="space-y-2">
            <span className="text-sm text-[var(--text-secondary)]">昵称</span>
            <Input value={form.nickName} onChange={(event) => updateField("nickName", event.target.value)} />
          </label>
          <label className="space-y-2">
            <span className="text-sm text-[var(--text-secondary)]">邮箱</span>
            <Input type="email" value={form.email} onChange={(event) => updateField("email", event.target.value)} />
          </label>
          <label className="space-y-2">
            <span className="text-sm text-[var(--text-secondary)]">学校</span>
            <Input value={form.schoolName} onChange={(event) => updateField("schoolName", event.target.value)} />
          </label>
          <label className="space-y-2">
            <span className="text-sm text-[var(--text-secondary)]">专业</span>
            <Input value={form.majorName} onChange={(event) => updateField("majorName", event.target.value)} />
          </label>
        </div>

        <label className="space-y-2">
          <span className="text-sm text-[var(--text-secondary)]">个人简介</span>
          <Textarea
            value={form.introduce}
            onChange={(event) => updateField("introduce", event.target.value)}
            placeholder="介绍一下你的方向、当前阶段和想通过 SynCode 达成什么目标。"
          />
        </label>

        {error ? <p className="text-sm text-[var(--danger)]">{error}</p> : null}
        {message ? <p className="text-sm text-[var(--success)]">{message}</p> : null}

        <div className="flex items-center gap-3">
          <Button type="submit" disabled={isSaving || isUploading}>
            {isSaving ? <LoaderCircle size={14} className="animate-spin" /> : null}
            保存资料
          </Button>
          <p className="text-sm text-[var(--text-muted)]">头像会通过现有 OSS 上传接口保存，昵称与简介直接写回用户资料。</p>
        </div>
      </form>
    </Panel>
  );
}
