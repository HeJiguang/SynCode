import * as React from "react";
import { ArrowRight, BookOpen, Clock3, Flame, Settings } from "lucide-react";
import { getPublicMessages, getSubmissionHistory, getTrainingSnapshot, getUserProfile } from "@aioj/api";
import { redirect } from "next/navigation";

import { AnnouncementCenter } from "../../components/announcement-center";
import { AppShell } from "../../components/app-shell";
import { SubmissionHeatmap } from "../../components/submission-heatmap";
import { appInternalPath, appPublicPath } from "../../lib/paths";
import { getServerAccessToken } from "../../lib/server-auth";
import { Panel, Tag } from "@aioj/ui";

function toneForTrainingStatus(status: string) {
  const normalized = String(status);
  if (normalized.includes("畬")) return "success" as const;
  if (normalized.includes("杩") || normalized.includes("行")) return "accent" as const;
  return "default" as const;
}

export default async function ProfilePage() {
  const token = await getServerAccessToken();
  if (!token) {
    redirect(appInternalPath("/login"));
  }

  const [profile, training, messages, submissions] = await Promise.all([
    getUserProfile(token),
    getTrainingSnapshot(token),
    getPublicMessages(token),
    getSubmissionHistory(undefined, token)
  ]);

  const focusLabel = training.tasks[0]?.focus || training.direction || "待设置训练方向";

  return (
    <AppShell
      rail={
        <>
          <AnnouncementCenter messages={messages.slice(0, 3)} />
          <Panel className="p-4">
            <p className="kicker">Quick Access</p>
            <div className="mt-3 space-y-2">
              {[
                { label: "进入设置", href: "/app/settings", icon: <Settings size={14} /> },
                { label: "查看训练计划", href: "/app/training", icon: <BookOpen size={14} /> }
              ].map((item) => (
                <a
                  key={item.label}
                  href={item.href.startsWith("/app/") ? appPublicPath(item.href.slice(4)) : item.href}
                  className="flex items-center justify-between rounded-[16px] border border-[var(--border-soft)] bg-[var(--surface-2)] px-3 py-2 text-sm text-[var(--text-primary)] transition hover:border-[var(--border-strong)]"
                >
                  <span className="flex items-center gap-2">
                    {item.icon}
                    {item.label}
                  </span>
                  <ArrowRight size={14} className="text-[var(--text-muted)]" />
                </a>
              ))}
            </div>
          </Panel>
        </>
      }
    >
      <Panel className="p-6" tone="strong">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex items-center gap-4">
            <div className="flex h-20 w-20 items-center justify-center overflow-hidden rounded-[24px] border border-[var(--border-soft)] bg-[var(--surface-2)] text-2xl font-semibold text-[var(--text-primary)]">
              {profile.headImage ? (
                <img src={profile.headImage} alt={profile.nickName} className="h-full w-full object-cover" />
              ) : (
                (profile.nickName || "S").slice(0, 1).toUpperCase()
              )}
            </div>
            <div>
              <p className="kicker">Profile</p>
              <h1 className="mt-1 text-3xl font-bold tracking-tight text-[var(--text-primary)]">{profile.nickName || "未设置昵称"}</h1>
              <p className="mt-2 max-w-2xl text-sm leading-7 text-[var(--text-secondary)]">
                {profile.headline || "还没有填写个人简介，可以去设置页补充你的方向与目标。"}
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                <Tag tone="accent">{focusLabel}</Tag>
                {profile.schoolName ? <Tag>{profile.schoolName}</Tag> : null}
                {profile.majorName ? <Tag>{profile.majorName}</Tag> : null}
              </div>
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-3">
            <div className="rounded-[20px] border border-[var(--border-soft)] bg-[var(--surface-2)] px-4 py-3">
              <p className="text-xs text-[var(--text-muted)]">已解题数</p>
              <p className="mt-2 text-2xl font-semibold text-[var(--text-primary)]">{profile.solvedCount}</p>
            </div>
            <div className="rounded-[20px] border border-[var(--border-soft)] bg-[var(--surface-2)] px-4 py-3">
              <p className="text-xs text-[var(--text-muted)]">提交总数</p>
              <p className="mt-2 text-2xl font-semibold text-[var(--text-primary)]">{profile.submissionCount}</p>
            </div>
            <div className="rounded-[20px] border border-[var(--border-soft)] bg-[var(--surface-2)] px-4 py-3">
              <p className="text-xs text-[var(--text-muted)]">连续学习</p>
              <p className="mt-2 flex items-center gap-2 text-2xl font-semibold text-[var(--text-primary)]">
                <Flame size={18} className="text-orange-400" />
                {profile.streakDays} 天
              </p>
            </div>
          </div>
        </div>
      </Panel>

      <Panel className="p-6">
        <div className="mb-5 flex items-center justify-between">
          <div>
            <p className="kicker">Activity</p>
            <h2 className="mt-1 text-xl font-semibold text-[var(--text-primary)]">提交热力图</h2>
          </div>
          <div className="flex items-center gap-2 text-sm text-[var(--text-muted)]">
            <Clock3 size={14} />
            近 24 周
          </div>
        </div>
        <SubmissionHeatmap data={profile.heatmap} weeks={24} />
      </Panel>

      <div className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
        <Panel className="overflow-hidden p-0">
          <div className="border-b border-[var(--border-soft)] px-6 py-5">
            <p className="kicker">Recent</p>
            <h2 className="mt-1 text-xl font-semibold text-[var(--text-primary)]">最近提交</h2>
          </div>
          <div className="divide-y divide-[var(--border-soft)]">
            {submissions.length > 0 ? (
              submissions.slice(0, 8).map((submission) => (
                <div key={submission.submissionId} className="flex items-center justify-between gap-4 px-6 py-4">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-[var(--text-primary)]">{submission.submissionId}</p>
                    <p className="mt-1 text-xs text-[var(--text-muted)]">
                      {submission.language} · {submission.submittedAt}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-medium text-[var(--text-primary)]">{submission.status}</p>
                    <p className="mt-1 text-xs text-[var(--text-muted)]">
                      {submission.runtime} · {submission.memory}
                    </p>
                  </div>
                </div>
              ))
            ) : (
              <div className="px-6 py-10 text-sm text-[var(--text-muted)]">当前还没有真实提交记录。</div>
            )}
          </div>
        </Panel>

        <div className="space-y-6">
          <Panel className="p-6">
            <p className="kicker">Training</p>
            <h2 className="mt-1 text-xl font-semibold text-[var(--text-primary)]">{training.title}</h2>
            <p className="mt-3 text-sm leading-7 text-[var(--text-secondary)]">
              {training.direction} · {training.level}
            </p>
            <p className="mt-3 text-sm text-[var(--text-muted)]">本周目标：{training.weeklyGoal}</p>
            <div className="mt-4 grid gap-3">
              {training.tasks.slice(0, 3).map((task) => (
                <div key={task.taskId} className="rounded-[18px] border border-[var(--border-soft)] bg-[var(--surface-2)] px-4 py-3">
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-sm font-medium text-[var(--text-primary)]">{task.title}</p>
                    <Tag tone={toneForTrainingStatus(task.status)}>
                      {task.status}
                    </Tag>
                  </div>
                  <p className="mt-2 text-xs text-[var(--text-muted)]">{task.focus}</p>
                </div>
              ))}
            </div>
          </Panel>

          <Panel className="p-6">
            <p className="kicker">Account</p>
            <div className="mt-3 space-y-3 text-sm text-[var(--text-secondary)]">
              <p>邮箱：{profile.email || "未设置"}</p>
              <p>学校：{profile.schoolName || "未设置"}</p>
              <p>专业：{profile.majorName || "未设置"}</p>
            </div>
            <a href={appPublicPath("/settings")} className="mt-4 inline-flex">
              <Tag tone="accent">前往资料设置</Tag>
            </a>
          </Panel>
        </div>
      </div>
    </AppShell>
  );
}
