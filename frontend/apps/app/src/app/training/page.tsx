import * as React from "react";
import { getPublicMessages, getTrainingSnapshot, getUserProfile } from "@aioj/api";
import { frontendPreviewMode } from "@aioj/config";
import { redirect } from "next/navigation";

import { AnnouncementCenter } from "../../components/announcement-center";
import { AppShell } from "../../components/app-shell";
import { TrainingActions } from "../../components/training-actions";
import { appInternalPath } from "../../lib/paths";
import { getTrainingStatusLabel, getTrainingStatusTone, withFallback } from "../../lib/presentation";
import { getServerAccessToken } from "../../lib/server-auth";
import { Panel, Tag } from "@aioj/ui";

export default async function TrainingPage() {
  const token = await getServerAccessToken();
  if (!token && !frontendPreviewMode) {
    redirect(appInternalPath("/login"));
  }

  const [training, profile, messages] = await Promise.all([
    getTrainingSnapshot(token),
    getUserProfile(token),
    getPublicMessages(token)
  ]);

  const trainingDirection = withFallback(training.direction, "待设置");
  const trainingLevel = withFallback(training.level, "待评估");
  const weeklyGoal = withFallback(training.weeklyGoal, "登录后生成训练计划");

  return (
    <AppShell demoMode={!token} rail={<AnnouncementCenter messages={messages.slice(0, 2)} />}>
      <div className="syncode-page-stack">
      <Panel tone="strong" className="syncode-page-hero p-5 md:p-6">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h1 className="text-3xl font-semibold tracking-[-0.05em] text-[var(--text-primary)] md:text-4xl">{training.title}</h1>
            <p className="mt-3 text-sm leading-7 text-[var(--text-secondary)]">
              {trainingDirection} · {trainingLevel}
            </p>
            <p className="mt-3 text-sm leading-7 text-[var(--text-secondary)]">{weeklyGoal}</p>
          </div>

          <div className="grid gap-3 sm:grid-cols-3">
            <div className="rounded-[18px] border border-[var(--border-soft)] bg-[var(--surface-3)] px-4 py-4">
              <p className="text-xs text-[var(--text-muted)]">完成度</p>
              <p className="mt-2 font-mono text-xl font-semibold text-[var(--text-primary)]">{training.completionRate}%</p>
            </div>
            <div className="rounded-[18px] border border-[var(--border-soft)] bg-[var(--surface-3)] px-4 py-4">
              <p className="text-xs text-[var(--text-muted)]">任务</p>
              <p className="mt-2 font-mono text-xl font-semibold text-[var(--text-primary)]">{training.tasks.length}</p>
            </div>
            <div className="rounded-[18px] border border-[var(--border-soft)] bg-[var(--surface-3)] px-4 py-4">
              <p className="text-xs text-[var(--text-muted)]">连续学习</p>
              <p className="mt-2 font-mono text-xl font-semibold text-[var(--text-primary)]">{profile.streakDays} 天</p>
            </div>
          </div>
        </div>
      </Panel>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.05fr)_minmax(0,0.95fr)]">
        <TrainingActions direction={training.direction} tasks={training.tasks} />

        <Panel className="syncode-page-section p-5">
          <h2 className="text-base font-semibold text-[var(--text-primary)]">当前任务</h2>
          <div className="mt-4 space-y-3">
            {training.tasks.length > 0 ? (
              training.tasks.map((task) => (
                <div key={task.taskId} className="rounded-[18px] border border-[var(--border-soft)] bg-[var(--surface-3)] p-4">
                  <div className="flex items-center justify-between gap-3">
                    <p className="font-semibold text-[var(--text-primary)]">{task.title}</p>
                    <Tag tone={getTrainingStatusTone(task)}>{getTrainingStatusLabel(task)}</Tag>
                  </div>
                  <p className="mt-2 text-sm text-[var(--text-secondary)]">
                    {task.focus} · {task.difficulty}
                  </p>
                </div>
              ))
            ) : (
              <div className="rounded-[18px] border border-dashed border-[var(--border-soft)] px-4 py-8 text-sm text-[var(--text-muted)]">
                当前还没有任务。
              </div>
            )}
          </div>
        </Panel>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Panel className="syncode-page-section p-5">
          <h2 className="text-base font-semibold text-[var(--text-primary)]">擅长</h2>
          <div className="mt-4 space-y-2 text-sm leading-7 text-[var(--text-secondary)]">
            {training.strengths.length > 0 ? training.strengths.map((item) => <p key={item}>{item}</p>) : <p>暂无数据。</p>}
          </div>
        </Panel>
        <Panel className="syncode-page-section p-5">
          <h2 className="text-base font-semibold text-[var(--text-primary)]">待补强</h2>
          <div className="mt-4 space-y-2 text-sm leading-7 text-[var(--text-secondary)]">
            {training.weaknesses.length > 0 ? training.weaknesses.map((item) => <p key={item}>{item}</p>) : <p>暂无数据。</p>}
          </div>
        </Panel>
      </div>
      </div>
    </AppShell>
  );
}
