import * as React from "react";
import { ArrowUpRight, Search, SlidersHorizontal, Sparkles, TimerReset } from "lucide-react";
import { getHotProblemList, getProblemList, getPublicMessages } from "@aioj/api";

import { AnnouncementCenter } from "../../components/announcement-center";
import { AppShell } from "../../components/app-shell";
import { HotProblemsPanel } from "../../components/hot-problems-panel";
import { getServerAccessToken } from "../../lib/server-auth";
import { Panel, Tag } from "@aioj/ui";

export default async function ProblemsPage() {
  const token = await getServerAccessToken();
  const [problems, hotProblems, messages] = await Promise.all([
    getProblemList(),
    getHotProblemList(),
    getPublicMessages(token)
  ]);
  const featuredTags = ["全部题目", "哈希表", "数组", "双指针", "动态规划", "二叉树", "回溯"];

  return (
    <AppShell
      demoMode={!token}
      rail={
        <>
          <HotProblemsPanel problems={hotProblems.slice(0, 3)} />
          <AnnouncementCenter messages={messages.slice(0, 2)} />
        </>
      }
    >
      <div className="syncode-page-stack">
      <Panel className="syncode-page-hero overflow-hidden p-0" tone="strong">
        <div className="border-b border-[var(--border-soft)] px-5 py-5 md:px-6 md:py-6">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div className="max-w-3xl">
              <p className="kicker">题库筛选</p>
              <h1 className="mt-2 text-3xl font-semibold tracking-[-0.04em] text-[var(--text-primary)] md:text-4xl">题库</h1>
            </div>
            <div className="flex flex-wrap gap-2">
              <Tag tone="accent">共 {problems.length} 题</Tag>
              <Tag>热题 {hotProblems.length} 道</Tag>
            </div>
          </div>
        </div>

        <div className="syncode-filter-strip px-5 py-5 md:px-6">
          <div className="flex flex-wrap gap-2">
            {featuredTags.map((tag, index) => (
              <a key={tag} href={index === 0 ? "/app/problems" : "/app/training"}>
                <Tag tone={index === 0 ? "accent" : "default"}>{tag}</Tag>
              </a>
            ))}
          </div>

          <div className="mt-5 grid gap-3 lg:grid-cols-[minmax(0,1fr)_160px_160px_200px]">
            <div className="flex items-center gap-3 rounded-[20px] border border-[var(--border-strong)] bg-[var(--surface-3)] px-4 py-3 text-sm text-[var(--text-secondary)]">
              <Search size={16} className="text-[var(--text-muted)]" />
              搜索题目、标签或专题
            </div>
            <div className="rounded-[20px] border border-[var(--border-soft)] bg-[var(--surface-3)] px-4 py-3 text-sm text-[var(--text-secondary)]">
              难度范围
            </div>
            <div className="rounded-[20px] border border-[var(--border-soft)] bg-[var(--surface-3)] px-4 py-3 text-sm text-[var(--text-secondary)]">
              题型筛选
            </div>
            <div className="flex items-center gap-3 rounded-[20px] border border-[var(--border-soft)] bg-[var(--surface-3)] px-4 py-3 text-sm text-[var(--text-secondary)]">
              <SlidersHorizontal size={16} className="text-[var(--text-muted)]" />
              排序: 热度 / 通过率
            </div>
          </div>
        </div>
      </Panel>

      <div className="syncode-problem-board">
        {problems.map((item, index) => (
          <a
            key={item.questionId}
            className="syncode-problem-entry group block rounded-[18px] border border-[var(--border-soft)] bg-[var(--surface-2)] p-5 transition hover:border-[var(--accent)]/25 hover:bg-[var(--surface-3)]"
            href={`/app/problems/${item.questionId}`}
          >
            <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_120px_120px_110px_56px] lg:items-center">
              <div className="flex min-w-0 gap-4">
                <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-[16px] border border-[var(--border-soft)] bg-[var(--surface-3)] text-sm font-semibold text-[var(--text-secondary)]">
                  {String(index + 1).padStart(2, "0")}
                </div>
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-3">
                    <h3 className="text-xl font-semibold text-[var(--text-primary)] transition-colors group-hover:text-[var(--accent)]">{item.title}</h3>
                    <Tag tone={item.difficulty === "Easy" ? "success" : item.difficulty === "Medium" ? "warning" : "danger"}>
                      {item.difficulty}
                    </Tag>
                    {item.trainingRecommended ? (
                      <Tag tone="accent">
                        <Sparkles size={12} className="mr-1" />
                        训练推荐
                      </Tag>
                    ) : null}
                  </div>
                  <p className="mt-2 text-sm leading-7 text-[var(--text-secondary)]">{item.tags.join(" / ")}</p>
                </div>
              </div>

              <div className="rounded-[18px] border border-[var(--border-soft)] bg-[var(--surface-3)] px-4 py-3 text-sm text-[var(--text-secondary)]">
                预计 {item.estimatedMinutes} 分钟
              </div>
              <div className="rounded-[18px] border border-[var(--border-soft)] bg-[var(--surface-3)] px-4 py-3 text-sm text-[var(--text-secondary)]">
                通过率 {item.acceptanceRate}
              </div>
              <div className="rounded-[18px] border border-[var(--border-soft)] bg-[var(--surface-3)] px-4 py-3 text-right">
                <p className="text-[11px] uppercase tracking-[0.16em] text-[var(--text-muted)]">热度</p>
                <p className="mt-1 text-lg font-semibold text-[var(--text-primary)]">{item.heat}</p>
              </div>
              <div className="hidden items-center justify-end gap-2 text-sm font-medium text-[var(--text-secondary)] lg:flex">
                <TimerReset size={15} />
                <ArrowUpRight size={14} className="transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
              </div>
            </div>
          </a>
        ))}
      </div>
      </div>
    </AppShell>
  );
}
