import * as React from "react";
import { ArrowRight, BookOpenText, Flame, Route, Trophy } from "lucide-react";
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
import { Button, Panel, Tag } from "@aioj/ui";

function getGreeting(name: string) {
  const currentHour = new Date().getHours();
  if (currentHour < 12) return `早上好，${name}`;
  if (currentHour < 18) return `下午好，${name}`;
  return `晚上好，${name}`;
}

function resolvePlanTone(statusLabel: string) {
  if (statusLabel.includes("完成")) return "success" as const;
  if (statusLabel.includes("进行")) return "accent" as const;
  return "default" as const;
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
        title: "暂无训练计划",
        direction: "待设置",
        level: "待评估",
        streakDays: 0,
        weeklyGoal: "登录后生成训练计划",
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
      privateDataError = "个人数据暂时不可用，请稍后刷新。";
    }
  }

  const nextWorkspaceQuestionId = hotProblems[0]?.questionId ?? problems[0]?.questionId ?? "1000";
  const latestSubmission = submissions[0];
  const currentTask = training.tasks[0];
  const featuredTopics = [
    { label: "哈希表", count: 42, href: "/problems" },
    { label: "双指针", count: 26, href: "/problems" },
    { label: "二叉树", count: 31, href: "/problems" },
    { label: "动态规划", count: 18, href: "/training" }
  ];

  return (
    <AppShell
      demoMode={!token}
      rail={
        <>
          <AnnouncementCenter messages={messages.slice(0, 3)} />
          <HotProblemsPanel problems={hotProblems.slice(0, 4)} />
          <Panel className="syncode-rail-panel p-5">
            <h3 className="text-base font-semibold text-[var(--text-primary)]">{profile.nickName || "未设置昵称"}</h3>
            {profile.headline ? <p className="mt-2 text-sm leading-6 text-[var(--text-muted)]">{profile.headline}</p> : null}
            <div className="mt-4 grid grid-cols-2 gap-3">
              <div className="rounded-[18px] border border-[var(--border-soft)] bg-[var(--surface-muted)] px-3 py-3">
                <p className="text-xs text-[var(--text-muted)]">已解题</p>
                <p className="mt-1 font-mono text-xl font-semibold text-[var(--text-primary)]">{profile.solvedCount}</p>
              </div>
              <div className="rounded-[18px] border border-[var(--border-soft)] bg-[var(--surface-muted)] px-3 py-3">
                <p className="text-xs text-[var(--text-muted)]">提交</p>
                <p className="mt-1 font-mono text-xl font-semibold text-[var(--text-primary)]">{profile.submissionCount}</p>
              </div>
            </div>
          </Panel>
        </>
      }
    >
      <div className="syncode-page-stack">
      <Panel tone="strong" className="syncode-page-hero p-5 md:p-6">
        <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_280px]">
          <div>
            <p className="text-sm text-[var(--text-secondary)]">{getGreeting(profile.nickName || "同学")}</p>
            <h1 className="mt-2 text-4xl font-semibold tracking-[-0.05em] text-[var(--text-primary)] md:text-5xl">开始刷题</h1>
            <div className="mt-6 flex flex-wrap gap-2">
              <a href={appPublicPath("/problems")}>
                <Button size="lg">
                  <BookOpenText size={16} />
                  开始刷题
                </Button>
              </a>
              <a href={appPublicPath("/training")}>
                <Button size="lg" variant="secondary">
                  <Route size={16} />
                  训练
                </Button>
              </a>
            </div>

            <div className="mt-6 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              {featuredTopics.map((topic) => (
                <a
                  key={topic.label}
                  href={appPublicPath(topic.href)}
                  className="rounded-[18px] border border-[var(--border-soft)] bg-[var(--surface-3)] px-4 py-4 transition-colors hover:bg-[var(--surface-1)]"
                >
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-sm font-semibold text-[var(--text-primary)]">{topic.label}</p>
                    <span className="font-mono text-xs text-[var(--text-muted)]">{topic.count}</span>
                  </div>
                </a>
              ))}
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-3 xl:grid-cols-1">
            <div className="rounded-[20px] border border-[var(--border-soft)] bg-[var(--surface-3)] p-4">
              <div className="flex items-center gap-2 text-[var(--text-secondary)]">
                <Flame size={15} />
                <span className="text-sm">连续学习</span>
              </div>
              <p className="mt-3 font-mono text-2xl font-semibold text-[var(--text-primary)]">{profile.streakDays} 天</p>
            </div>
            <div className="rounded-[20px] border border-[var(--border-soft)] bg-[var(--surface-3)] p-4">
              <p className="text-sm text-[var(--text-secondary)]">进度</p>
              <p className="mt-3 font-mono text-2xl font-semibold text-[var(--text-primary)]">{training.completionRate}%</p>
            </div>
            <div className="rounded-[20px] border border-[var(--border-soft)] bg-[var(--surface-3)] p-4">
              <div className="flex items-center gap-2 text-[var(--text-secondary)]">
                <Trophy size={15} />
                <span className="text-sm">最近提交</span>
              </div>
              <p className="mt-3 text-sm font-semibold text-[var(--text-primary)]">{latestSubmission?.status ?? "暂无"}</p>
            </div>
          </div>
        </div>
      </Panel>

      {privateDataError ? (
        <Panel className="border-[var(--warning)]/30 bg-[var(--warning-bg)] p-4 text-sm text-[var(--warning)]">
          {privateDataError}
        </Panel>
      ) : null}

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.15fr)_minmax(0,0.85fr)]">
        <Panel className="syncode-page-section p-5">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-lg font-semibold text-[var(--text-primary)]">当前任务</h2>
            {currentTask ? <Tag tone={resolvePlanTone(currentTask.status)}>{currentTask.status}</Tag> : null}
          </div>

          {currentTask ? (
            <div className="mt-4 rounded-[20px] border border-[var(--border-soft)] bg-[var(--surface-3)] p-4">
              <p className="text-base font-semibold text-[var(--text-primary)]">{currentTask.title}</p>
              <p className="mt-2 text-sm text-[var(--text-secondary)]">{currentTask.focus}</p>
              <div className="mt-4">
                <a href={appPublicPath(`/workspace/${nextWorkspaceQuestionId}`)} className="inline-flex">
                  <Button size="sm" variant="secondary">去做题</Button>
                </a>
              </div>
            </div>
          ) : (
            <div className="mt-4 rounded-[20px] border border-dashed border-[var(--border-soft)] px-4 py-8 text-sm text-[var(--text-muted)]">
              暂无任务。
            </div>
          )}

          <div className="syncode-dashboard-focus-list mt-5 divide-y divide-[var(--border-soft)] overflow-hidden rounded-[16px] border border-[var(--border-soft)]">
            {training.tasks.length > 0 ? (
              training.tasks.map((task) => (
                <div key={task.taskId} className="flex items-center justify-between gap-3 px-4 py-4">
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-[var(--text-primary)]">{task.title}</p>
                    <p className="mt-1 text-xs text-[var(--text-muted)]">{task.focus}</p>
                  </div>
                  <Tag tone={resolvePlanTone(task.status)}>{task.status}</Tag>
                </div>
              ))
            ) : (
              <div className="px-4 py-8 text-sm text-[var(--text-muted)]">暂无任务。</div>
            )}
          </div>
        </Panel>

        <Panel className="syncode-page-section p-5">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-lg font-semibold text-[var(--text-primary)]">本周</h2>
            <a href={appPublicPath("/problems")} className="inline-flex items-center gap-2 text-sm font-medium text-[var(--text-secondary)] hover:text-[var(--text-primary)]">
              题库
              <ArrowRight size={14} />
            </a>
          </div>
          <p className="mt-3 text-sm leading-7 text-[var(--text-secondary)]">{training.weeklyGoal}</p>

          <div className="mt-5 grid gap-4 md:grid-cols-2">
            <div className="rounded-[20px] border border-[var(--border-soft)] bg-[var(--surface-muted)] p-4">
              <p className="text-sm font-medium text-[var(--text-primary)]">擅长</p>
              <div className="mt-3 space-y-2 text-sm leading-6 text-[var(--text-secondary)]">
                {training.strengths.length > 0 ? training.strengths.map((item) => <p key={item}>{item}</p>) : <p>暂无数据。</p>}
              </div>
            </div>
            <div className="rounded-[20px] border border-[var(--border-soft)] bg-[var(--surface-muted)] p-4">
              <p className="text-sm font-medium text-[var(--text-primary)]">待补强</p>
              <div className="mt-3 space-y-2 text-sm leading-6 text-[var(--text-secondary)]">
                {training.weaknesses.length > 0 ? training.weaknesses.map((item) => <p key={item}>{item}</p>) : <p>暂无数据。</p>}
              </div>
            </div>
          </div>
        </Panel>
      </div>
      </div>
    </AppShell>
  );
}
