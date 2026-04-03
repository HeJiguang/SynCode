import * as React from "react";
import { Activity, Flame, Sparkles } from "lucide-react";
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
import { DashboardKpiCard } from "../components/dashboard/dashboard-kpi-card";
import { DashboardModule } from "../components/dashboard/dashboard-module";
import { DashboardTaskList } from "../components/dashboard/dashboard-task-list";
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
      privateDataError = "个人数据暂时不可用。当前先展示公开内容，请稍后刷新。";
    }
  }

  const nextWorkspaceQuestionId = hotProblems[0]?.questionId ?? problems[0]?.questionId ?? "two-sum";
  const latestSubmission = submissions[0];
  const currentFocus = training.tasks[0]?.focus || training.direction || "待设置训练方向";
  const currentTask = training.tasks[0];

  return (
    <AppShell
      demoMode={!token}
      rail={
        <>
          <AnnouncementCenter messages={messages.slice(0, 3)} />
          <HotProblemsPanel problems={hotProblems.slice(0, 4)} />
          <Panel className="p-5">
            <p className="kicker">Profile</p>
            <h3 className="mt-2 text-lg font-semibold text-[var(--text-primary)]">{profile.nickName || "未设置昵称"}</h3>
            <p className="mt-2 text-sm leading-6 text-[var(--text-muted)]">
              {profile.headline || "补全学校、专业与个人介绍后，你的训练档案会更完整。"}
            </p>
            <div className="mt-5 grid grid-cols-2 gap-3">
              <div className="rounded-[var(--radius-sm)] border border-[var(--border-soft)] bg-[var(--surface-muted)] px-3 py-3">
                <p className="text-[11px] uppercase tracking-[0.12em] text-[var(--text-faint)]">已解题</p>
                <p className="mt-2 font-mono text-xl font-semibold text-[var(--text-primary)]">{profile.solvedCount}</p>
              </div>
              <div className="rounded-[var(--radius-sm)] border border-[var(--border-soft)] bg-[var(--surface-muted)] px-3 py-3">
                <p className="text-[11px] uppercase tracking-[0.12em] text-[var(--text-faint)]">提交数</p>
                <p className="mt-2 font-mono text-xl font-semibold text-[var(--text-primary)]">{profile.submissionCount}</p>
              </div>
            </div>
          </Panel>
        </>
      }
    >
      <Panel tone="strong" className="hero-grid overflow-hidden p-7 md:p-8">
        <div className="relative flex flex-col gap-8 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-3xl">
            <p className="kicker">Today</p>
            <h1 className="section-title mt-3">{getGreeting(profile.nickName || "开发者")}</h1>
            <p className="mt-4 max-w-2xl text-[15px] leading-8 text-[var(--text-secondary)]">
              这里聚合了训练计划、近期提交、题目热度和系统动态。首页的目标不是展示所有信息，而是把你下一步最值得做的动作放到最前面。
            </p>
            <div className="mt-6 flex flex-wrap gap-2.5">
              <Tag tone="accent">当前焦点 {currentFocus}</Tag>
              <Tag>{training.level}</Tag>
              <Tag>连续学习 {profile.streakDays} 天</Tag>
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-3 lg:w-[540px]">
            <div className="rounded-[var(--radius-card)] border border-[var(--border-soft)] bg-[var(--surface-1)] p-4">
              <p className="text-[11px] uppercase tracking-[0.12em] text-[var(--text-faint)]">本周目标</p>
              <p className="mt-2 text-sm leading-6 text-[var(--text-primary)]">{training.weeklyGoal}</p>
            </div>
            <div className="rounded-[var(--radius-card)] border border-[var(--border-soft)] bg-[var(--surface-1)] p-4">
              <p className="text-[11px] uppercase tracking-[0.12em] text-[var(--text-faint)]">当前计划</p>
              <p className="mt-2 text-sm font-medium text-[var(--text-primary)]">{training.title}</p>
            </div>
            <div className="rounded-[var(--radius-card)] border border-[var(--border-soft)] bg-[var(--surface-1)] p-4">
              <p className="text-[11px] uppercase tracking-[0.12em] text-[var(--text-faint)]">下一步</p>
              <a href={appPublicPath(`/workspace/${nextWorkspaceQuestionId}`)} className="mt-2 inline-flex">
                <Button size="sm">进入工作区</Button>
              </a>
            </div>
          </div>
        </div>
      </Panel>

      {privateDataError ? (
        <Panel className="border-[var(--warning)]/30 bg-[var(--warning-bg)] p-4 text-sm text-[var(--warning)]">
          {privateDataError}
        </Panel>
      ) : null}

      <div className="grid gap-4 md:grid-cols-3">
        <DashboardKpiCard
          label="连续学习"
          value={`${profile.streakDays} 天`}
          detail="保持节奏比堆积任务更重要。"
          icon={<Flame size={16} />}
        />
        <DashboardKpiCard
          label="计划进度"
          value={`${training.completionRate}%`}
          detail={training.title}
          icon={<Sparkles size={16} />}
        />
        <DashboardKpiCard
          label="最近提交"
          value={latestSubmission?.status ?? "暂无"}
          detail={latestSubmission ? `${latestSubmission.language} · ${latestSubmission.submittedAt}` : "登录后查看个人提交记录"}
          icon={<Activity size={16} />}
        />
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.25fr)_minmax(320px,0.75fr)]">
        <div className="space-y-6">
          <DashboardModule
            eyebrow="Primary Work"
            title="当前训练主线"
            description="把最重要的计划、任务和入口放在同一个工作面板里，降低切换成本。"
            badge={training.direction}
            tone="strong"
            footer={
              <div className="flex flex-wrap items-center gap-3">
                <Tag tone={resolvePlanTone(currentTask?.status ?? "待开始")}>{currentTask?.status ?? "待开始"}</Tag>
                <span className="text-sm text-[var(--text-muted)]">
                  {currentTask ? `当前任务：${currentTask.title}` : "当前还没有激活中的训练任务。"}
                </span>
              </div>
            }
          >
            <DashboardTaskList tasks={training.tasks} />
          </DashboardModule>

          <DashboardModule
            eyebrow="Strengths"
            title="训练总结"
            description="保留少量但关键的自我反馈，让首页承担“方向确认”而不是“信息堆砌”。"
          >
            <div className="grid gap-4 md:grid-cols-2">
              <div className="rounded-[var(--radius-card)] border border-[var(--border-soft)] bg-[var(--surface-muted)] p-5">
                <p className="kicker">优势方向</p>
                <div className="mt-4 space-y-2 text-sm leading-6 text-[var(--text-secondary)]">
                  {training.strengths.length > 0 ? training.strengths.map((item) => <p key={item}>{item}</p>) : <p>暂无总结数据。</p>}
                </div>
              </div>
              <div className="rounded-[var(--radius-card)] border border-[var(--border-soft)] bg-[var(--surface-muted)] p-5">
                <p className="kicker">待补强项</p>
                <div className="mt-4 space-y-2 text-sm leading-6 text-[var(--text-secondary)]">
                  {training.weaknesses.length > 0 ? training.weaknesses.map((item) => <p key={item}>{item}</p>) : <p>暂无弱项分析数据。</p>}
                </div>
              </div>
            </div>
          </DashboardModule>
        </div>

        <div className="space-y-6">
          <DashboardModule
            eyebrow="Problem Flow"
            title="热门题入口"
            description="保留高频动作，但降低视觉权重，让它成为辅助区而不是主角。"
          >
            <HotProblemsPanel problems={hotProblems} />
          </DashboardModule>
        </div>
      </div>
    </AppShell>
  );
}
