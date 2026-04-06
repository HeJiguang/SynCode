import * as React from "react";
import { ArrowRight, BookOpen, Clock3, Flame, Settings, Sparkles } from "lucide-react";
import { getPublicMessages, getSubmissionHistory, getTrainingSnapshot, getUserProfile } from "@aioj/api";
import { frontendPreviewMode } from "@aioj/config";
import { redirect } from "next/navigation";

import { AnnouncementCenter } from "../../components/announcement-center";
import { AppShell } from "../../components/app-shell";
import { SubmissionHeatmap } from "../../components/submission-heatmap";
import { appInternalPath, appPublicPath } from "../../lib/paths";
import { getTrainingStatusLabel, getTrainingStatusTone, withFallback } from "../../lib/presentation";
import { getServerAccessToken } from "../../lib/server-auth";
import { Panel, Tag } from "@aioj/ui";

export default async function ProfilePage() {
  const token = await getServerAccessToken();
  if (!token && !frontendPreviewMode) {
    redirect(appInternalPath("/login"));
  }

  const [profile, training, messages, submissions] = await Promise.all([
    getUserProfile(token),
    getTrainingSnapshot(token),
    getPublicMessages(token),
    getSubmissionHistory(undefined, token)
  ]);

  const focusLabel = withFallback(training.tasks[0]?.focus, withFallback(training.direction, "待设置训练方向"));
  const headline = withFallback(profile.headline, "");
  const nickName = withFallback(profile.nickName, "未设置昵称");
  const weeklyGoal = withFallback(training.weeklyGoal, "登录后生成个性化训练计划");

  return (
    <AppShell
      demoMode={!token}
      rail={
        <>
          <AnnouncementCenter messages={messages.slice(0, 3)} />
          <Panel className="p-4">
            <p className="kicker">快捷入口</p>
            <div className="mt-3 space-y-2">
              {[
                { label: "进入设置", href: "/app/settings", icon: <Settings size={14} /> },
                { label: "查看训练计划", href: "/app/training", icon: <BookOpen size={14} /> }
              ].map((item) => (
                <a
                  key={item.label}
                  href={item.href.startsWith("/app/") ? appPublicPath(item.href.slice(4)) : item.href}
                  className="flex items-center justify-between rounded-[16px] border border-[var(--border-soft)] bg-[var(--surface-2)] px-3 py-2 text-sm text-[var(--text-primary)] transition-all duration-300 ease-out hover:border-[var(--border-strong)] hover:bg-[var(--surface-1)]"
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
      <Panel className="hero-grid overflow-hidden p-6 md:p-7" tone="strong">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex items-center gap-4">
            <div className="flex h-20 w-20 items-center justify-center overflow-hidden rounded-[24px] border border-[var(--border-soft)] bg-[var(--surface-2)] text-2xl font-semibold text-[var(--text-primary)]">
              {profile.headImage ? (
                <img src={profile.headImage} alt={nickName} className="h-full w-full object-cover" />
              ) : (
                nickName.slice(0, 1).toUpperCase()
              )}
            </div>
            <div>
              <p className="kicker">我的</p>
              <h1 className="mt-1 text-3xl font-semibold tracking-[-0.04em] text-[var(--text-primary)]">{nickName}</h1>
              {headline ? <p className="mt-2 max-w-2xl text-sm leading-7 text-[var(--text-secondary)]">{headline}</p> : null}
              <div className="mt-3 flex flex-wrap gap-2">
                <Tag tone="accent">{focusLabel}</Tag>
                {profile.schoolName ? <Tag>{profile.schoolName}</Tag> : null}
                {profile.majorName ? <Tag>{profile.majorName}</Tag> : null}
              </div>
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-3 lg:min-w-[420px]">
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

        <div className="mt-6 grid gap-3 md:grid-cols-3">
          <div className="rounded-[18px] border border-[var(--border-soft)] bg-white/[0.03] px-4 py-4">
            <p className="text-xs text-[var(--text-muted)]">当前焦点</p>
            <p className="mt-2 text-sm font-semibold leading-6 text-[var(--text-primary)]">{focusLabel}</p>
          </div>
          <div className="rounded-[18px] border border-[var(--border-soft)] bg-white/[0.03] px-4 py-4">
            <p className="text-xs text-[var(--text-muted)]">本周目标</p>
            <p className="mt-2 text-sm font-semibold leading-6 text-[var(--text-primary)]">{weeklyGoal}</p>
          </div>
          <div className="rounded-[18px] border border-[var(--border-soft)] bg-white/[0.03] px-4 py-4">
            <p className="text-xs text-[var(--text-muted)]">建议动作</p>
            <a href={appPublicPath("/training")} className="mt-2 inline-flex items-center gap-2 text-sm font-semibold text-[var(--accent)] transition-opacity duration-300 ease-out hover:opacity-80">
              <Sparkles size={14} />
              去训练
            </a>
          </div>
        </div>
      </Panel>

      <Panel className="p-6">
        <div className="mb-5 flex items-center justify-between">
          <div>
            <p className="kicker">提交</p>
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
            <p className="kicker">记录</p>
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
            <p className="kicker">训练</p>
            <h2 className="mt-1 text-xl font-semibold text-[var(--text-primary)]">{training.title}</h2>
            <p className="mt-3 text-sm leading-7 text-[var(--text-secondary)]">
              {withFallback(training.direction, "待设置训练方向")} · {withFallback(training.level, "待评估")}
            </p>
            <p className="mt-3 text-sm text-[var(--text-muted)]">本周目标：{weeklyGoal}</p>
            <div className="mt-4 grid gap-3">
              {training.tasks.slice(0, 3).map((task) => (
                <div key={task.taskId} className="rounded-[18px] border border-[var(--border-soft)] bg-[var(--surface-2)] px-4 py-3">
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-sm font-medium text-[var(--text-primary)]">{task.title}</p>
                    <Tag tone={getTrainingStatusTone(task)}>{getTrainingStatusLabel(task)}</Tag>
                  </div>
                  <p className="mt-2 text-xs text-[var(--text-muted)]">{task.focus}</p>
                </div>
              ))}
            </div>
          </Panel>

          <Panel className="p-6">
            <p className="kicker">账号</p>
            <h2 className="mt-1 text-xl font-semibold text-[var(--text-primary)]">账号信息</h2>
            <div className="mt-3 space-y-3 text-sm text-[var(--text-secondary)]">
              <p>邮箱：{withFallback(profile.email, "未设置")}</p>
              <p>学校：{withFallback(profile.schoolName, "未设置")}</p>
              <p>专业：{withFallback(profile.majorName, "未设置")}</p>
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
