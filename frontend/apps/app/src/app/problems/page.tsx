import * as React from "react";
import { ArrowUpRight, Sparkles, TimerReset } from "lucide-react";
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
      <Panel className="hero-grid overflow-hidden p-6 md:p-7" tone="strong">
        <div className="relative flex flex-col gap-6">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div className="max-w-3xl">
              <p className="kicker">题库浏览</p>
              <h1 className="mt-2 text-3xl font-bold tracking-[-0.04em] text-[var(--text-primary)] md:text-4xl">先选一题，再进入工作区持续推进</h1>
              <p className="mt-3 max-w-2xl text-sm leading-7 text-[var(--text-secondary)] md:text-[15px]">
                题库页聚合了当前热题、训练推荐和基础筛选信息，帮助你更快决定今天要解决什么问题。
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Tag tone="accent">共 {problems.length} 题</Tag>
              <Tag>热题 {hotProblems.length} 道</Tag>
            </div>
          </div>

          <div className="grid gap-3 md:grid-cols-4">
            <div className="rounded-[18px] border border-[var(--border-soft)] bg-black/10 px-4 py-3 text-sm text-[var(--text-secondary)]">
              搜索建议: 哈希表 / 区间 / 回溯
            </div>
            <div className="rounded-[18px] border border-[var(--border-soft)] bg-black/10 px-4 py-3 text-sm text-[var(--text-secondary)]">
              难度范围: 全部
            </div>
            <div className="rounded-[18px] border border-[var(--border-soft)] bg-black/10 px-4 py-3 text-sm text-[var(--text-secondary)]">
              当前偏好: 热题优先
            </div>
            <div className="rounded-[18px] border border-[var(--border-soft)] bg-black/10 px-4 py-3 text-sm text-[var(--text-secondary)]">
              排序方式: 热度 / 推荐度
            </div>
          </div>
        </div>
      </Panel>

      <div className="space-y-4">
        {problems.map((item, index) => (
          <a
            key={item.questionId}
            className="group block rounded-[24px] border border-[var(--border-soft)] bg-[var(--surface-muted)] p-5 transition hover:-translate-y-0.5 hover:border-[var(--border-strong)] hover:bg-[var(--surface-1)] hover:shadow-[var(--shadow-panel)]"
            href={`/app/problems/${item.questionId}`}
          >
            <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
              <div className="flex min-w-0 gap-4">
                <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-[16px] border border-[var(--border-soft)] bg-[var(--surface-2)] text-sm font-semibold text-[var(--text-secondary)]">
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
                  <p className="mt-2 text-sm leading-7 text-[var(--text-secondary)]">
                    {item.tags.join(" / ")} · 预计 {item.estimatedMinutes} 分钟 · 通过率 {item.acceptanceRate}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-4">
                <div className="rounded-[18px] border border-[var(--border-soft)] bg-black/10 px-4 py-3 text-right">
                  <p className="text-[11px] uppercase tracking-[0.16em] text-[var(--text-muted)]">热度</p>
                  <p className="mt-1 text-lg font-semibold text-[var(--text-primary)]">{item.heat}</p>
                </div>
                <div className="hidden items-center gap-2 text-sm font-medium text-[var(--text-secondary)] lg:flex">
                  <TimerReset size={15} />
                  查看详情
                  <ArrowUpRight size={14} className="transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
                </div>
              </div>
            </div>
          </a>
        ))}
      </div>
    </AppShell>
  );
}
