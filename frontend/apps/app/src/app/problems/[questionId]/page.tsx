import * as React from "react";
import { getHotProblemList, getProblemDetail } from "@aioj/api";

import { AppShell } from "../../../components/app-shell";
import { HotProblemsPanel } from "../../../components/hot-problems-panel";
import { getServerAccessToken } from "../../../lib/server-auth";
import { Button, Panel, Tag } from "@aioj/ui";

type PageProps = {
  params: Promise<{ questionId: string }>;
};

export default async function ProblemDetailPage({ params }: PageProps) {
  const { questionId } = await params;
  const token = await getServerAccessToken();
  const [detail, hotProblems] = await Promise.all([getProblemDetail(questionId, token), getHotProblemList()]);

  return (
    <AppShell demoMode={!token} rail={<HotProblemsPanel problems={hotProblems.slice(0, 3)} />}>
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div className="space-y-1">
          <p className="kicker">Question Detail</p>
          <h1 className="text-2xl font-bold tracking-tight text-[var(--text-primary)]">{detail.title}</h1>
          <p className="max-w-xl text-sm leading-7 text-[var(--text-secondary)]">{detail.summary}</p>
        </div>
        <div className="shrink-0">
          <a href={`/app/workspace/${detail.questionId}`}>
            <Button className="h-10 px-6 font-semibold shadow-sm" id="btn-enter-workspace">
              进入工作区开始训练
            </Button>
          </a>
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.04fr_0.96fr]">
        <Panel className="p-6" tone="strong">
          <div className="flex flex-wrap items-center gap-3">
            <Tag tone={detail.difficulty === "Easy" ? "success" : detail.difficulty === "Medium" ? "warning" : "danger"}>
              {detail.difficulty}
            </Tag>
            {detail.tags.map((item) => (
              <Tag key={item}>{item}</Tag>
            ))}
          </div>
          <div className="mt-5 space-y-4">
            {detail.content.map((item) => (
              <p key={item} className="text-sm leading-8 text-[var(--text-secondary)]">
                {item}
              </p>
            ))}
          </div>
        </Panel>

        <Panel className="p-6">
          <p className="kicker">题目信息</p>
          <div className="mt-5 grid gap-4 md:grid-cols-2">
            <div className="rounded-[18px] border border-[var(--border-soft)] bg-black/20 p-4">
              <p className="text-sm text-[var(--text-muted)]">算法标签</p>
              <p className="mt-2 text-lg font-semibold text-[var(--text-primary)]">{detail.algorithmTag}</p>
            </div>
            <div className="rounded-[18px] border border-[var(--border-soft)] bg-black/20 p-4">
              <p className="text-sm text-[var(--text-muted)]">预计用时</p>
              <p className="mt-2 text-lg font-semibold text-[var(--text-primary)]">{detail.estimatedMinutes} 分钟</p>
            </div>
          </div>

          <div className="mt-5 rounded-[18px] border border-[var(--border-soft)] bg-white/4 p-4">
            <p className="text-sm text-[var(--text-muted)]">约束条件</p>
            <ul className="mt-3 space-y-2 text-sm leading-7 text-[var(--text-secondary)]">
              {detail.constraints.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>

          <div className="mt-5 rounded-[18px] border border-[var(--border-soft)] bg-white/4 p-4">
            <p className="text-sm text-[var(--text-muted)]">示例用例</p>
            <div className="mt-3 space-y-3">
              {detail.examples.map((item, index) => (
                <div key={`${item.input}-${index}`} className="rounded-[16px] border border-[var(--border-soft)] bg-black/15 p-4">
                  <p className="text-xs font-medium uppercase tracking-wider text-[var(--text-muted)]">Input</p>
                  <pre className="mt-2 whitespace-pre-wrap font-mono text-sm text-[var(--text-primary)]">{item.input}</pre>
                  <p className="mt-3 text-xs font-medium uppercase tracking-wider text-[var(--text-muted)]">Output</p>
                  <pre className="mt-2 whitespace-pre-wrap font-mono text-sm text-[var(--text-primary)]">{item.output}</pre>
                </div>
              ))}
            </div>
          </div>
        </Panel>
      </div>
    </AppShell>
  );
}
