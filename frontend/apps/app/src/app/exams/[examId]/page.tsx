import * as React from "react";
import { getExamDetail, getProblemDetail, getSubmissionHistory } from "@aioj/api";

import { AppShell } from "../../../components/app-shell";
import { EditorPanel } from "../../../components/editor-panel";
import { JudgePanel } from "../../../components/judge-panel";
import { getServerAccessToken } from "../../../lib/server-auth";
import { Panel, Tag } from "@aioj/ui";

type PageProps = {
  params: Promise<{ examId: string }>;
};

export default async function ExamWorkspacePage({ params }: PageProps) {
  const { examId } = await params;
  const token = await getServerAccessToken();
  const exam = await getExamDetail(examId, token);
  const questionId = exam.firstQuestionId;

  if (!questionId) {
    return (
      <AppShell demoMode={!token}>
        <Panel className="p-6">
          <p className="kicker">Exam</p>
          <h1 className="mt-1 text-2xl font-semibold text-[var(--text-primary)]">{exam.title}</h1>
          <p className="mt-4 text-sm leading-7 text-[var(--text-secondary)]">
            当前考试还没有可进入的题目，或者首题合同暂未准备完成。请先检查考试题目配置。
          </p>
        </Panel>
      </AppShell>
    );
  }

  const [detail, submissions] = await Promise.all([
    getProblemDetail(questionId, token),
    getSubmissionHistory(questionId, token, examId)
  ]);
  const questionContent = detail.content.join("\n\n");

  return (
    <AppShell
      eyebrow="Exam Mode"
      title={exam.title}
      description="考试工作区会把状态、剩余时间和当前题号放在更靠前的位置。"
    >
      <Panel className="p-5" tone="strong">
        <div className="grid gap-4 md:grid-cols-4">
          <div className="rounded-[18px] border border-[var(--border-soft)] bg-black/20 p-4">
            <p className="text-sm text-[var(--text-muted)]">状态</p>
            <p className="mt-2 text-lg font-semibold">{exam.status}</p>
          </div>
          <div className="rounded-[18px] border border-[var(--border-soft)] bg-black/20 p-4">
            <p className="text-sm text-[var(--text-muted)]">剩余时间</p>
            <p className="mt-2 text-lg font-semibold">49:32</p>
          </div>
          <div className="rounded-[18px] border border-[var(--border-soft)] bg-black/20 p-4">
            <p className="text-sm text-[var(--text-muted)]">当前题号</p>
            <p className="mt-2 text-lg font-semibold">1 / {exam.questionCount}</p>
          </div>
          <div className="rounded-[18px] border border-[var(--border-soft)] bg-black/20 p-4">
            <p className="text-sm text-[var(--text-muted)]">导航</p>
            <p className="mt-2 text-lg font-semibold">受控切题</p>
          </div>
        </div>
      </Panel>

      <div className="grid gap-4 2xl:grid-cols-[0.82fr_1.18fr]">
        <Panel className="p-6" tone="strong">
          <div className="flex items-center gap-3">
            <Tag tone="warning">Exam</Tag>
            <Tag>{detail.algorithmTag}</Tag>
            <Tag tone="accent">Heat {detail.heat}</Tag>
          </div>
          <h3 className="mt-4 text-xl font-semibold">{detail.title}</h3>
          <div className="mt-5 space-y-4">
            {detail.content.map((item) => (
              <p key={item} className="text-sm leading-8 text-[var(--text-secondary)]">
                {item}
              </p>
            ))}
          </div>
        </Panel>

        <div className="grid gap-4">
          <JudgePanel questionId={questionId} examId={examId} submissions={submissions} />
          <EditorPanel
            initialCode={detail.starterCode}
            questionId={questionId}
            examId={examId}
            questionTitle={detail.title}
            questionContent={questionContent}
            examples={detail.examples}
          />
        </div>
      </div>
    </AppShell>
  );
}
