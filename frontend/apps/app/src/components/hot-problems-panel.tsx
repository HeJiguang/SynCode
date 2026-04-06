import * as React from "react";
import type { QuestionListItem } from "@aioj/api";

import { Panel, Tag } from "@aioj/ui";
import { appPublicPath } from "../lib/paths";

type HotProblemsPanelProps = {
  problems: QuestionListItem[];
};

export function HotProblemsPanel({ problems }: HotProblemsPanelProps) {
  return (
    <Panel className="syncode-rail-panel flex flex-col p-0">
      <div className="border-b border-[var(--border-soft)] px-5 py-4">
        <h3 className="text-base font-semibold text-[var(--text-primary)]">热门题</h3>
      </div>

      <div className="flex-1 divide-y divide-[var(--border-soft)]">
        {problems.map((item, index) => (
          <a
            key={item.questionId}
            className="group flex items-start gap-3 px-5 py-4 transition-colors hover:bg-[var(--surface-2)]"
            href={appPublicPath(`/workspace/${item.questionId}`)}
          >
            <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-[12px] border border-[var(--border-soft)] bg-[var(--surface-1)] font-mono text-[12px] font-semibold text-[var(--text-secondary)]">
              {index + 1}
            </span>

            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <h4 className="text-sm font-semibold text-[var(--text-primary)] transition-colors group-hover:text-[var(--accent)]">
                  {item.title}
                </h4>
                <Tag tone={item.difficulty === "Easy" ? "success" : item.difficulty === "Medium" ? "warning" : "danger"}>
                  {item.difficulty}
                </Tag>
              </div>
              <p className="mt-1 text-[13px] leading-6 text-[var(--text-muted)]">
                {item.tags.join(" / ")} · {item.estimatedMinutes} 分钟 · 通过率 {item.acceptanceRate}
              </p>
            </div>

            <div className="shrink-0 font-mono text-[12px] text-[var(--text-muted)]">{item.heat}</div>
          </a>
        ))}
      </div>
    </Panel>
  );
}
