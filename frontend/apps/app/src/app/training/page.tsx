import * as React from "react";
import { getPublicMessages, getTrainingSnapshot, getUserProfile } from "@aioj/api";
import { redirect } from "next/navigation";

import { AnnouncementCenter } from "../../components/announcement-center";
import { AppShell } from "../../components/app-shell";
import { TrainingActions } from "../../components/training-actions";
import { appInternalPath } from "../../lib/paths";
import { getServerAccessToken } from "../../lib/server-auth";
import { Panel, Tag } from "@aioj/ui";

function toneForTrainingStatus(status: string) {
  const normalized = String(status);
  if (normalized.includes("畬")) return "success" as const;
  if (normalized.includes("杩") || normalized.includes("行")) return "accent" as const;
  return "default" as const;
}

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

  return (
    <AppShell rail={<AnnouncementCenter messages={messages.slice(0, 2)} />}>
      <div className="grid gap-4 xl:grid-cols-[0.96fr_1.04fr]">
        <Panel className="p-5" tone="accent">
          <p className="kicker">Profile</p>
          <h2 className="mt-2 text-2xl font-semibold text-[var(--text-primary)]">{training.title}</h2>
          <p className="mt-3 text-sm leading-7 text-[var(--text-secondary)]">
            {training.direction} · {training.level}
          </p>
          <p className="mt-4 text-sm text-[var(--text-secondary)]">本周目标：{training.weeklyGoal}</p>
          <div className="mt-5 flex flex-wrap gap-2">
            <Tag tone="accent">连续学习 {profile.streakDays} 天</Tag>
            <Tag>{profile.solvedCount} 题已解决</Tag>
          </div>
          <div className="mt-5">
            <TrainingActions direction={training.direction} tasks={training.tasks} />
          </div>
        </Panel>

        <Panel className="p-5">
          <p className="kicker">Progress</p>
          <h2 className="mt-2 text-xl font-semibold text-[var(--text-primary)]">当前任务</h2>
          <p className="mt-2 text-sm text-[var(--text-muted)]">完成度 {training.completionRate}%</p>
          <div className="mt-5 space-y-3">
            {training.tasks.length > 0 ? (
              training.tasks.map((task) => (
                <div key={task.taskId} className="rounded-[18px] border border-[var(--border-soft)] bg-black/20 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <p className="font-semibold text-[var(--text-primary)]">{task.title}</p>
                    <Tag tone={toneForTrainingStatus(task.status)}>
                      {task.status}
                    </Tag>
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
        <Panel className="p-5">
          <p className="kicker">Strengths</p>
          <div className="mt-4 space-y-2 text-sm leading-7 text-[var(--text-secondary)]">
            {training.strengths.length > 0 ? training.strengths.map((item) => <p key={item}>{item}</p>) : <p>暂无总结数据。</p>}
          </div>
        </Panel>
        <Panel className="p-5">
          <p className="kicker">Weaknesses</p>
          <div className="mt-4 space-y-2 text-sm leading-7 text-[var(--text-secondary)]">
            {training.weaknesses.length > 0 ? training.weaknesses.map((item) => <p key={item}>{item}</p>) : <p>暂无弱项分析数据。</p>}
          </div>
        </Panel>
      </div>
    </AppShell>
  );
}
