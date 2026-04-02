import * as React from "react";
import { Activity, Flame, Medal, Sparkles } from "lucide-react";
import {
  getHotProblemList,
  getProblemList,
  getPublicMessages,
  getSubmissionHistory,
  getTrainingSnapshot,
  getUserProfile
} from "@aioj/api";

import { AnnouncementCenter } from "../components/announcement-center";
import { AppShell } from "../components/app-shell";
import { HotProblemsPanel } from "../components/hot-problems-panel";
import { appPublicPath } from "../lib/paths";
import { getServerAccessToken } from "../lib/server-auth";
import { Panel, Tag } from "@aioj/ui";

function toneForTrainingStatus(status: string) {
  const normalized = String(status);
  if (normalized.includes("畬")) return "success" as const;
  if (normalized.includes("杩") || normalized.includes("行")) return "accent" as const;
  return "default" as const;
}

function getGreeting(name: string) {
  const currentHour = new Date().getHours();
  if (currentHour < 12) return `早上好，${name}`;
  if (currentHour < 18) return `下午好，${name}`;
  return `晚上好，${name}`;
}

export default async function DashboardPage() {
  const token = await getServerAccessToken();
  const [hotProblems, problems, messages] = await Promise.all([
    getHotProblemList(),
    getProblemList(),
    getPublicMessages(token)
  ]);

  let training = token
    ? {
        title: "当前暂无训练计划",
        direction: "待设置训练方向",
        level: "待评估",
        streakDays: 0,
        weeklyGoal: "用户侧真实训练数据加载中",
        completionRate: 0,
        strengths: [],
        weaknesses: [],
        tasks: []
      }
    : await getTrainingSnapshot();
  let profile = token
    ? {
        headImage: undefined,
        nickName: "已登录用户",
        email: "",
        schoolName: "",
        majorName: "",
        headline: "",
        solvedCount: 0,
        submissionCount: 0,
        trainingHours: 0,
        streakDays: 0,
        heatmap: {},
        recentFocus: "",
        timezone: "Asia/Shanghai",
        preferredLanguage: "java" as const,
        notifyByEmail: true,
        editorTheme: "vs-dark" as const,
        shortcuts: []
      }
    : await getUserProfile();
  let submissions = token ? [] : await getSubmissionHistory(undefined, token);
  let privateDataError: string | null = null;

  if (token) {
    try {
      const nextWorkspaceQuestionId = hotProblems[0]?.questionId ?? problems[0]?.questionId;
      [training, profile, submissions] = await Promise.all([
        getTrainingSnapshot(token),
        getUserProfile(token),
        getSubmissionHistory(nextWorkspaceQuestionId, token)
      ]);
    } catch {
      privateDataError = "已登录，但个人侧数据暂时不可用。当前先展示公开内容，请稍后刷新。";
    }
  }

  const nextWorkspaceQuestionId = hotProblems[0]?.questionId ?? problems[0]?.questionId ?? "two-sum";
  const latestSubmission = submissions[0];
  const focusLabel = training.tasks[0]?.focus || training.direction || "待设置训练方向";

  return (
    <AppShell
      demoMode={!token}
      rail={
        <>
          <HotProblemsPanel problems={hotProblems.slice(0, 4)} />
          <AnnouncementCenter messages={messages.slice(0, 3)} />
        </>
      }
    >
      <Panel className="hero-grid overflow-hidden p-7 md:p-8" tone="strong">
        <div className="relative flex flex-col gap-8 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-3xl">
            <p className="kicker">今日工作台</p>
            <h1 className="mt-3 max-w-2xl text-4xl font-bold leading-tight tracking-[-0.05em] text-[var(--text-primary)] md:text-5xl">
              {getGreeting(profile.nickName || "开发者")}
            </h1>
            <p className="mt-4 max-w-2xl text-[15px] leading-8 text-[var(--text-secondary)] md:text-base">
              这里聚合了热题、训练计划、最近提交和系统动态。登录后，你会直接回到自己的训练节奏里。
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <Tag tone="accent">当前焦点 {focusLabel}</Tag>
              <Tag>{training.title}</Tag>
              <Tag>连续学习 {profile.streakDays} 天</Tag>
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-3 lg:min-w-[460px]">
            <div className="rounded-[20px] border border-[var(--border-soft)] bg-black/10 px-4 py-4">
              <p className="text-xs text-[var(--text-muted)]">本周目标</p>
              <p className="mt-2 text-sm font-semibold leading-6 text-[var(--text-primary)]">{training.weeklyGoal}</p>
            </div>
            <div className="rounded-[20px] border border-[var(--border-soft)] bg-black/10 px-4 py-4">
              <p className="text-xs text-[var(--text-muted)]">训练状态</p>
              <p className="mt-2 text-sm font-semibold leading-6 text-[var(--text-primary)]">{training.level}</p>
            </div>
            <div className="rounded-[20px] border border-[var(--border-soft)] bg-black/10 px-4 py-4">
              <p className="text-xs text-[var(--text-muted)]">推荐入口</p>
              <a href={appPublicPath(`/workspace/${nextWorkspaceQuestionId}`)} className="mt-2 inline-flex text-sm font-semibold text-[var(--accent)] transition-opacity hover:opacity-80">
                进入工作区
              </a>
            </div>
          </div>
        </div>
      </Panel>

      {privateDataError ? (
        <Panel className="mb-6 border-[var(--warning)]/30 bg-[var(--warning-bg)] p-4 text-sm text-[var(--warning)]">
          {privateDataError}
        </Panel>
      ) : null}

      <div className="grid gap-5 md:grid-cols-3">
        <Panel className="p-5">
          <div className="flex items-center gap-3">
            <Flame size={18} className="text-orange-400" />
            <p className="text-sm font-medium text-[var(--text-secondary)]">连续学习</p>
          </div>
          <p className="mt-4 font-mono text-3xl font-bold text-[var(--text-primary)]">{profile.streakDays} 天</p>
          <p className="mt-2 text-sm leading-6 text-[var(--text-muted)]">根据最近提交与训练进度持续更新，帮助你保持节奏。</p>
        </Panel>
        <Panel className="p-5">
          <div className="flex items-center gap-3">
            <Sparkles size={18} className="text-cyan-300" />
            <p className="text-sm font-medium text-[var(--text-secondary)]">当前计划</p>
          </div>
          <p className="mt-4 text-xl font-semibold text-[var(--text-primary)]">{training.title}</p>
          <p className="mt-2 text-sm leading-6 text-[var(--text-muted)]">
            {training.level} · {training.weeklyGoal}
          </p>
        </Panel>
        <Panel className="p-5">
          <div className="flex items-center gap-3">
            <Activity size={18} className="text-emerald-300" />
            <p className="text-sm font-medium text-[var(--text-secondary)]">最近提交</p>
          </div>
          <p className="mt-4 text-xl font-semibold text-[var(--text-primary)]">{latestSubmission?.status ?? "暂无提交"}</p>
          <p className="mt-2 text-sm leading-6 text-[var(--text-muted)]">
            {latestSubmission ? `${latestSubmission.language} · ${latestSubmission.submittedAt}` : "登录后可查看最近提交与判题结果。"}
          </p>
        </Panel>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <HotProblemsPanel problems={hotProblems} />

        <Panel hoverable className="flex flex-col p-0">
          <div className="flex items-center justify-between border-b border-[var(--border-soft)] p-6">
            <div>
              <p className="kicker">训练路径</p>
              <h3 className="mt-1 text-lg font-bold text-[var(--text-primary)]">阶段训练计划</h3>
            </div>
            <Tag tone="accent">{training.direction}</Tag>
          </div>
          <div className="bg-[var(--surface-2)] px-6 py-4">
            <p className="text-sm font-medium text-[var(--text-secondary)]">
              完成度 {training.completionRate}% · 当前关注 {focusLabel}
            </p>
          </div>
          <div className="divide-y divide-[var(--border-soft)]">
            {training.tasks.length > 0 ? (
              training.tasks.map((task) => (
                <div key={task.taskId} className="flex items-center justify-between gap-4 px-6 py-5 transition-colors hover:bg-[var(--surface-2)]">
                  <div className="min-w-0">
                    <p className="text-[15px] font-semibold text-[var(--text-primary)]">{task.title}</p>
                    <p className="mt-1.5 text-sm leading-6 text-[var(--text-muted)]">聚焦 {task.focus}</p>
                  </div>
                  <Tag tone={toneForTrainingStatus(task.status)}>
                    {task.status}
                  </Tag>
                </div>
              ))
            ) : (
              <div className="px-6 py-10 text-sm text-[var(--text-muted)]">当前还没有可展示的训练任务。</div>
            )}
          </div>
        </Panel>
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <AnnouncementCenter messages={messages} />
        <Panel className="p-6">
          <p className="kicker">个人概览</p>
          <h3 className="mt-1 text-lg font-bold text-[var(--text-primary)]">{profile.nickName || "未设置昵称"}</h3>
          <p className="mt-2 text-sm leading-6 text-[var(--text-secondary)]">
            {profile.headline || "去设置页补充你的学校、专业和个人简介，让训练档案更完整。"}
          </p>
          <div className="mt-5 grid gap-4 sm:grid-cols-3">
            <div className="rounded-[18px] border border-[var(--border-soft)] bg-black/15 p-4">
              <p className="text-xs font-medium uppercase tracking-wider text-[var(--text-muted)]">已解题数</p>
              <p className="mt-2 font-mono text-2xl font-bold text-[var(--text-primary)]">{profile.solvedCount}</p>
            </div>
            <div className="rounded-[18px] border border-[var(--border-soft)] bg-black/15 p-4">
              <p className="text-xs font-medium uppercase tracking-wider text-[var(--text-muted)]">提交总数</p>
              <p className="mt-2 font-mono text-2xl font-bold text-[var(--text-primary)]">{profile.submissionCount}</p>
            </div>
            <div className="rounded-[18px] border border-[var(--border-soft)] bg-black/15 p-4">
              <p className="text-xs font-medium uppercase tracking-wider text-[var(--text-muted)]">训练焦点</p>
              <p className="mt-2 text-sm font-semibold text-[var(--text-primary)]">{focusLabel}</p>
            </div>
          </div>
          <a href={appPublicPath(`/workspace/${nextWorkspaceQuestionId}`)} className="mt-5 inline-flex">
            <Tag tone="accent">进入当前推荐工作区</Tag>
          </a>
        </Panel>
      </div>
    </AppShell>
  );
}
