import * as React from "react";
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
      <Panel className="p-5" tone="strong">
        <div className="grid gap-3 md:grid-cols-4">
          <div className="rounded-[18px] border border-[var(--border-soft)] bg-black/20 px-4 py-3 text-sm text-[var(--text-secondary)]">
            搜索: 哈希表 / 区间 / 回溯
          </div>
          <div className="rounded-[18px] border border-[var(--border-soft)] bg-black/20 px-4 py-3 text-sm text-[var(--text-secondary)]">
            难度: All
          </div>
          <div className="rounded-[18px] border border-[var(--border-soft)] bg-black/20 px-4 py-3 text-sm text-[var(--text-secondary)]">
            标签: 热题优先
          </div>
          <div className="rounded-[18px] border border-[var(--border-soft)] bg-black/20 px-4 py-3 text-sm text-[var(--text-secondary)]">
            排序: 热度 / 推荐度
          </div>
        </div>
      </Panel>

      <div className="space-y-3">
        {problems.map((item) => (
          <a
            key={item.questionId}
            className="block rounded-[22px] border border-[var(--border-soft)] bg-[var(--surface-muted)] p-5 transition hover:border-[var(--border-strong)] hover:bg-[var(--surface-1)]"
            href={`/app/problems/${item.questionId}`}
          >
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
              <div className="space-y-3">
                <div className="flex flex-wrap items-center gap-3">
                  <h3 className="text-xl font-semibold text-[var(--text-primary)]">{item.title}</h3>
                  <Tag tone={item.difficulty === "Easy" ? "success" : item.difficulty === "Medium" ? "warning" : "danger"}>
                    {item.difficulty}
                  </Tag>
                  {item.trainingRecommended ? <Tag tone="accent">训练推荐</Tag> : null}
                </div>
                <p className="text-sm text-[var(--text-secondary)]">
                  {item.tags.join(" / ")} · 预计 {item.estimatedMinutes} 分钟 · 通过率 {item.acceptanceRate}
                </p>
              </div>
              <div className="text-sm text-[var(--text-muted)]">热度 {item.heat}</div>
            </div>
          </a>
        ))}
      </div>
    </AppShell>
  );
}
