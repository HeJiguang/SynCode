import * as React from "react";
import { getProblemDetail, getSubmissionHistory } from "@aioj/api";
import { Clock, HardDrive, Hash } from "lucide-react";

import { Tabs, Tag } from "@aioj/ui";
import { AiPanel } from "../../../components/ai-panel";
import { AppShell } from "../../../components/app-shell";
import { EditorPanel } from "../../../components/editor-panel";
import { JudgePanel } from "../../../components/judge-panel";
import { getServerAccessToken } from "../../../lib/server-auth";
import { WorkspaceLayout } from "./workspace-layout";

type PageProps = {
  params: Promise<{ questionId: string }>;
};

export default async function WorkspacePage({ params }: PageProps) {
  const { questionId } = await params;
  const token = await getServerAccessToken();

  const [detail, submissions] = await Promise.all([
    getProblemDetail(questionId, token),
    getSubmissionHistory(questionId, token)
  ]);

  const questionContent = detail.content.join("\n\n");

  const questionDescription = (
    <div className="flex h-full flex-col overflow-hidden">
      <div className="shrink-0 border-b border-[var(--border-soft)] bg-[var(--surface-1)] px-5 py-5">
        <div className="flex flex-wrap items-center gap-2.5">
          <Tag tone={detail.difficulty === "Easy" ? "success" : detail.difficulty === "Medium" ? "warning" : "danger"}>
            {detail.difficulty}
          </Tag>
          {detail.tags.map((item) => (
            <Tag key={item}>{item}</Tag>
          ))}
          <Tag tone="accent">热度 {detail.heat}</Tag>
        </div>

        <div className="mt-4 max-w-2xl">
          <p className="kicker">Current Task</p>
          <h2 className="mt-2 text-2xl font-semibold tracking-[-0.03em] text-[var(--text-primary)]">{detail.title}</h2>
          <p className="mt-3 text-[13px] leading-relaxed text-[var(--text-secondary)]">{detail.summary}</p>
        </div>

        <div className="mt-5 grid grid-cols-3 gap-2.5">
          <div className="flex items-center gap-2 rounded-[10px] border border-[var(--border-soft)] bg-[var(--surface-2)] px-3 py-2">
            <Clock size={14} className="shrink-0 text-[var(--text-muted)]" />
            <span className="text-xs font-semibold">{detail.timeLimit} ms</span>
          </div>
          <div className="flex items-center gap-2 rounded-[10px] border border-[var(--border-soft)] bg-[var(--surface-2)] px-3 py-2">
            <HardDrive size={14} className="shrink-0 text-[var(--text-muted)]" />
            <span className="text-xs font-semibold">{detail.spaceLimit / 1024} MB</span>
          </div>
          <div className="flex items-center gap-2 rounded-[10px] border border-[var(--border-soft)] bg-[var(--surface-2)] px-3 py-2">
            <Hash size={14} className="shrink-0 text-[var(--text-muted)]" />
            <span className="truncate text-xs font-semibold">{detail.algorithmTag}</span>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-auto px-5 py-4">
        <div className="space-y-4">
          <h3 className="text-base font-semibold text-[var(--text-primary)]">题目说明</h3>
          {detail.content.map((item, index) => (
            <p key={index} className="text-[14px] leading-relaxed text-[var(--text-secondary)]">
              {item}
            </p>
          ))}
        </div>

        <div className="mt-7 grid gap-3">
          <div className="rounded-[10px] border border-[var(--border-soft)] bg-[var(--surface-1)] p-4">
            <p className="text-sm font-semibold text-[var(--text-primary)]">输入输出示例</p>
            <div className="mt-3 space-y-3">
              {detail.examples.map((example, index) => (
                <div
                  key={`${example.input}-${index}`}
                  className="rounded-[10px] border border-[var(--border-soft)] bg-[var(--surface-2)] p-4 font-mono text-[13px] leading-relaxed text-[var(--text-muted)]"
                >
                  <p>
                    <strong className="mr-2 font-sans text-xs text-[var(--text-primary)]">IN:</strong>
                    {example.input}
                  </p>
                  <p className="mt-1.5">
                    <strong className="mr-2 font-sans text-xs text-[var(--text-primary)]">OUT:</strong>
                    {example.output}
                  </p>
                  {example.note ? (
                    <p className="mt-3 border-t border-[var(--border-soft)] pt-3 font-sans text-xs text-[var(--text-muted)]">
                      {example.note}
                    </p>
                  ) : null}
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-[10px] border border-[var(--border-soft)] bg-[var(--surface-1)] p-4">
            <p className="mb-3 text-sm font-semibold text-[var(--text-primary)]">边界与提示</p>
            <ul className="list-disc space-y-2 pl-4 text-[13px] leading-relaxed text-[var(--text-secondary)] marker:text-[var(--text-muted)]">
              {detail.hints.map((item, index) => (
                <li key={index} className="pl-1">
                  {item}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <AppShell immersive demoMode={!token}>
      <WorkspaceLayout
        aiPanel={
          <AiPanel
            initialArtifacts={[]}
            questionId={questionId}
            questionTitle={detail.title}
            questionContent={questionContent}
          />
        }
        questionPanel={
          <Tabs
            defaultTab="description"
            className="h-full"
            tabs={[
              { id: "description", label: "题目说明", content: questionDescription },
              {
                id: "submissions",
                label: "提交结果",
                content: (
                  <div className="h-full p-0">
                    <JudgePanel questionId={questionId} submissions={submissions} />
                  </div>
                )
              }
            ]}
          />
        }
        editorPanel={
          <EditorPanel
            initialCode={detail.starterCode}
            questionId={questionId}
            questionTitle={detail.title}
            questionContent={questionContent}
            examples={detail.examples}
          />
        }
      />
    </AppShell>
  );
}
