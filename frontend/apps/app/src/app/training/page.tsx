import * as React from "react";
import { Sparkles, Target, TrendingUp } from "lucide-react";
import { getPublicMessages, getTrainingSnapshot, getUserProfile } from "@aioj/api";
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
  if (!token) {
    redirect(appInternalPath("/login"));
  }

  const [training, profile, messages] = await Promise.all([
    getTrainingSnapshot(token),
    getUserProfile(token),
    getPublicMessages(token)
  ]);

  const trainingDirection = withFallback(training.direction, "待设置训练方向");
  const trainingLevel = withFallback(training.level, "待评估");
  const weeklyGoal = withFallback(training.weeklyGoal, "登录后生成个性化训练计划");

  return (
    <AppShell rail={<AnnouncementCenter messages={messages.slice(0, 2)} />}>
      <Panel className="hero-grid overflow-hidden border border-white/10 bg-white/[0.03] p-6 backdrop-blur-md md:p-7" tone="accent">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-3xl">
            <p className="kicker">Training Overview</p>
            <h1 className="mt-2 text-3xl font-semibold tracking-[-0.05em] text-[var(--text-primary)] md:text-5xl">{training.title}</h1>
            <p className="mt-4 text-sm leading-7 text-[var(--text-secondary)] md:text-[15px]">
              {trainingDirection} · {trainingLevel}
            </p>
            <p className="mt-4 max-w-2xl text-sm leading-8 text-[var(--text-secondary)]">本周目标：{weeklyGoal}</p>
            <div className="mt-5 flex flex-wrap gap-2">
              <Tag tone="accent">连续学习 {profile.streakDays} 天</Tag>
              <Tag>{profile.solvedCount} 题已解决</Tag>
            </div>
          </div>
          <div className="grid gap-3 md:grid-cols-3 lg:min-w-[460px]">
            <div className="rounded-[18px] border border-white/10 bg-white/[0.02] px-4 py-4 transition-all duration-300 ease-out hover:border-white/20 hover:bg-white/[0.04]">
              <p className="text-xs text-[var(--text-muted)]">完成度</p>
              <p className="mt-2 inline-flex items-center gap-2 text-lg font-semibold text-[var(--text-primary)]">
                <TrendingUp size={16} className="text-[var(--accent)]" />
                {training.completionRate}%
              </p>
            </div>
            <div className="rounded-[18px] border border-white/10 bg-white/[0.02] px-4 py-4 transition-all duration-300 ease-out hover:border-white/20 hover:bg-white/[0.04]">
              <p className="text-xs text-[var(--text-muted)]">任务数</p>
              <p className="mt-2 inline-flex items-center gap-2 text-lg font-semibold text-[var(--text-primary)]">
                <Target size={16} className="text-[var(--accent)]" />
                {training.tasks.length} 项
              </p>
            </div>
            <div className="rounded-[18px] border border-white/10 bg-white/[0.02] px-4 py-4 transition-all duration-300 ease-out hover:border-white/20 hover:bg-white/[0.04]">
              <p className="text-xs text-[var(--text-muted)]">下一步</p>
              <p className="mt-2 inline-flex items-center gap-2 text-sm font-semibold text-[var(--text-primary)]">
                <Sparkles size={16} className="text-[var(--accent)]" />
                继续推进当前计划
              </p>
            </div>
          </div>
        </div>
      </Panel>

      <div className="grid gap-4 xl:grid-cols-[0.96fr_1.04fr]">
        <Panel className="border border-white/10 bg-white/[0.03] p-5 backdrop-blur-md" tone="accent">
          <p className="kicker">Plan Context</p>
          <h2 className="mt-2 text-2xl font-semibold text-[var(--text-primary)]">当前训练主线</h2>
          <p className="mt-3 text-sm leading-7 text-[var(--text-secondary)]">
            {trainingDirection} · {trainingLevel}
          </p>
          <p className="mt-4 text-sm text-[var(--text-secondary)]">本周目标：{weeklyGoal}</p>
          <div className="mt-5 flex flex-wrap gap-2">
            <Tag tone="accent">连续学习 {profile.streakDays} 天</Tag>
            <Tag>{profile.solvedCount} 题已解决</Tag>
          </div>
          <div className="mt-5">
            <TrainingActions direction={training.direction} tasks={training.tasks} />
          </div>
        </Panel>

        <Panel className="border border-white/10 bg-white/[0.03] p-5 backdrop-blur-md">
          <p className="kicker">Task Progress</p>
          <h2 className="mt-2 text-xl font-semibold text-[var(--text-primary)]">当前任务</h2>
          <p className="mt-2 text-sm text-[var(--text-muted)]">完成度 {training.completionRate}%</p>
          <div className="mt-5 space-y-3">
            {training.tasks.length > 0 ? (
              training.tasks.map((task) => (
                <div key={task.taskId} className="rounded-[18px] border border-white/10 bg-white/[0.02] p-4 transition-all duration-300 ease-out hover:border-white/20 hover:bg-white/[0.04]">
                  <div className="flex items-center justify-between gap-3">
                    <p className="font-semibold text-[var(--text-primary)]">{task.title}</p>
                    <Tag tone={getTrainingStatusTone(task)}>{getTrainingStatusLabel(task)}</Tag>
                  </div>
                  <p className="mt-2 text-sm text-[var(--text-secondary)]">
                    聚焦 {task.focus} · 难度 {task.difficulty}
                  </p>
                </div>
              ))
            ) : (
              <div className="rounded-[18px] border border-dashed border-[var(--border-soft)] px-4 py-8 text-sm text-[var(--text-muted)]">
                当前还没有生成中的训练任务。
              </div>
            )}
          </div>
        </Panel>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Panel className="border border-white/10 bg-white/[0.03] p-5 backdrop-blur-md">
          <p className="kicker">Strengths</p>
          <h2 className="mt-2 text-xl font-semibold text-[var(--text-primary)]">优势方向</h2>
          <div className="mt-4 space-y-2 text-sm leading-7 text-[var(--text-secondary)]">
            {training.strengths.length > 0 ? training.strengths.map((item) => <p key={item}>{item}</p>) : <p>训练总结会在生成计划后逐步出现。</p>}
          </div>
        </Panel>
        <Panel className="border border-white/10 bg-white/[0.03] p-5 backdrop-blur-md">
          <p className="kicker">Weak Points</p>
          <h2 className="mt-2 text-xl font-semibold text-[var(--text-primary)]">待补强项</h2>
          <div className="mt-4 space-y-2 text-sm leading-7 text-[var(--text-secondary)]">
            {training.weaknesses.length > 0 ? training.weaknesses.map((item) => <p key={item}>{item}</p>) : <p>生成你的第一份计划后，这里会开始聚焦需要加强的方向。</p>}
          </div>
        </Panel>
      </div>
    </AppShell>
  );
}
