import * as React from "react";
import type { QuestionListItem } from "@aioj/api";
import { Flame } from "lucide-react";

import { Panel, Tag } from "@aioj/ui";
import { appPublicPath } from "../lib/paths";

type HotProblemsPanelProps = {
  problems: QuestionListItem[];
};

export function HotProblemsPanel({ problems }: HotProblemsPanelProps) {
  return (
    <Panel hoverable className="flex flex-col p-0">
      <div className="flex items-center justify-between border-b border-[var(--border-soft)] p-6 pb-5">
        <div>
          <p className="kicker">热门题目</p>
          <h3 className="mt-1 text-lg font-bold text-[var(--text-primary)]">热题榜</h3>
        </div>
        <div className="flex items-center gap-1.5 text-[13px] font-medium text-[var(--text-muted)]">
          <Flame size={14} className="text-[var(--warning)]" />
          最近访问热度
        </div>
      </div>

      <div className="flex-1 divide-y divide-[var(--border-soft)]">
        {problems.map((item, index) => (
          <a
            key={item.questionId}
            className="group flex items-start gap-4 p-6 transition-colors hover:bg-[var(--surface-2)]"
            href={appPublicPath(`/workspace/${item.questionId}`)}
          >
            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-[var(--radius-sm)] border border-[var(--border-soft)] bg-[var(--surface-1)] font-mono text-[13px] font-bold tabular-nums text-[var(--text-secondary)] shadow-sm">
              {index + 1}
            </span>

            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2.5">
                <h4 className="text-[15px] font-semibold text-[var(--text-primary)] transition-colors group-hover:text-[var(--accent)]">
                  {item.title}
                </h4>
                <Tag tone={item.difficulty === "Easy" ? "success" : item.difficulty === "Medium" ? "warning" : "danger"}>
                  {item.difficulty}
                </Tag>
              </div>
              <p className="mt-1.5 text-[13px] leading-relaxed text-[var(--text-muted)]">
                {item.tags.join(" / ")} · 预计 {item.estimatedMinutes} 分钟 · 通过率 {item.acceptanceRate}
              </p>
            </div>

            <div className="flex shrink-0 items-center justify-center rounded-[var(--radius-sm)] border border-[var(--border-soft)] bg-[var(--surface-1)] px-2 py-1 font-mono text-[13px] font-medium tabular-nums text-[var(--text-muted)]">
              {item.heat}
            </div>
          </a>
        ))}
      </div>
    </Panel>
  );
}
