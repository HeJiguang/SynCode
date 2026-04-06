import * as React from "react";
import { AlertTriangle, Clock3, FileQuestion, ListOrdered, ShieldCheck, TimerReset } from "lucide-react";
import { getExamDetail, getProblemDetail, getSubmissionHistory } from "@aioj/api";

import { AppShell } from "../../../components/app-shell";
import { EditorPanel } from "../../../components/editor-panel";
import { JudgePanel } from "../../../components/judge-panel";
import { getServerAccessToken } from "../../../lib/server-auth";
import { Panel, Tag } from "@aioj/ui";

type PageProps = {
  params: Promise<{ examId: string }>;
};

const UPCOMING_STATUS = "鏈紑濮?" as const;
const ACTIVE_STATUS = "杩涜涓?" as const;
const FINISHED_STATUS = "宸茬粨鏉?" as const;

function getExamTone(status: string) {
  if (status === ACTIVE_STATUS) return "warning" as const;
  if (status === FINISHED_STATUS) return "default" as const;
  return "accent" as const;
}

function getExamStatusLabel(status: string) {
  if (status === ACTIVE_STATUS) return "进行中";
  if (status === FINISHED_STATUS) return "已结束";
  return "未开始";
}

function ErrorState({
  title,
  message,
  icon
}: {
  title: string;
  message: string;
  icon: React.ReactNode;
}) {
  return (
    <AppShell>
      <Panel className="border border-[var(--border-soft)] bg-[var(--surface-2)] p-8">
        <div className="flex items-start gap-4">
          <div className="rounded-2xl border border-[var(--border-soft)] bg-[var(--surface-3)] p-3 text-[var(--text-secondary)]">{icon}</div>
          <div className="space-y-2">
            <p className="kicker">考试</p>
            <h1 className="text-2xl font-semibold text-[var(--text-primary)]">{title}</h1>
            <p className="max-w-2xl text-sm leading-7 text-[var(--text-secondary)]">{message}</p>
          </div>
        </div>
      </Panel>
    </AppShell>
  );
}

export default async function ExamWorkspacePage({ params }: PageProps) {
  const { examId } = await params;
  const token = await getServerAccessToken();

  let exam;
  try {
    exam = await getExamDetail(examId, token);
  } catch (error) {
    return (
      <ErrorState
        title="考试信息加载失败"
        message={error instanceof Error ? error.message : "请稍后刷新页面，或返回考试列表重新进入。"}
        icon={<AlertTriangle size={18} />}
      />
    );
  }

  const questionId = exam.firstQuestionId;

  if (!questionId) {
    return (
      <ErrorState
        title={exam.title}
        message="当前没有可进入的题目。"
        icon={<FileQuestion size={18} />}
      />
    );
  }

  let detail;
  let submissions;
  try {
    [detail, submissions] = await Promise.all([
      getProblemDetail(questionId, token),
      getSubmissionHistory(questionId, token, examId)
    ]);
  } catch (error) {
    return (
      <ErrorState
        title="题面加载失败"
        message={error instanceof Error ? error.message : "请稍后刷新页面，或返回考试列表重新进入。"}
        icon={<FileQuestion size={18} />}
      />
    );
  }

  const questionContent = detail.content.join("\n\n");

  return (
    <AppShell immersive>
      <div className="h-full overflow-auto px-5 py-6 md:px-8">
        <div className="mx-auto grid max-w-[1680px] gap-4">
          <Panel className="border border-[var(--border-soft)] bg-[var(--surface-2)] p-6" tone="strong">
            <div className="flex flex-col gap-6 2xl:flex-row 2xl:items-end 2xl:justify-between">
              <div className="max-w-4xl">
                <div className="flex flex-wrap items-center gap-3">
                  <p className="kicker">考试</p>
                  <Tag tone={getExamTone(exam.status)}>{getExamStatusLabel(exam.status)}</Tag>
                </div>
                <h1 className="mt-3 text-3xl font-semibold tracking-[-0.05em] text-[var(--text-primary)] md:text-4xl">{exam.title}</h1>
              </div>

              <div className="grid gap-3 md:grid-cols-4">
                <div className="rounded-[18px] border border-[var(--border-soft)] bg-[var(--surface-3)] p-4 transition-all duration-300 ease-out hover:border-[var(--border-strong)] hover:bg-[var(--surface-1)]">
                  <p className="flex items-center gap-2 text-sm text-[var(--text-muted)]">
                    <ShieldCheck size={14} />
                    状态
                  </p>
                  <div className="mt-3">
                    <Tag tone={getExamTone(exam.status)}>{getExamStatusLabel(exam.status)}</Tag>
                  </div>
                </div>
                <div className="rounded-[18px] border border-[var(--border-soft)] bg-[var(--surface-3)] p-4 transition-all duration-300 ease-out hover:border-[var(--border-strong)] hover:bg-[var(--surface-1)]">
                  <p className="flex items-center gap-2 text-sm text-[var(--text-muted)]">
                    <Clock3 size={14} />
                    时间区间
                  </p>
                  <p className="mt-3 text-sm font-medium leading-7 text-[var(--text-primary)]">{exam.startTime} - {exam.endTime}</p>
                </div>
                <div className="rounded-[18px] border border-[var(--border-soft)] bg-[var(--surface-3)] p-4 transition-all duration-300 ease-out hover:border-[var(--border-strong)] hover:bg-[var(--surface-1)]">
                  <p className="flex items-center gap-2 text-sm text-[var(--text-muted)]">
                    <TimerReset size={14} />
                    时长
                  </p>
                  <p className="mt-3 text-lg font-semibold text-[var(--text-primary)]">{exam.durationMinutes} 分钟</p>
                </div>
                <div className="rounded-[18px] border border-[var(--border-soft)] bg-[var(--surface-3)] p-4 transition-all duration-300 ease-out hover:border-[var(--border-strong)] hover:bg-[var(--surface-1)]">
                  <p className="flex items-center gap-2 text-sm text-[var(--text-muted)]">
                    <ListOrdered size={14} />
                    当前题号
                  </p>
                  <p className="mt-3 text-lg font-semibold text-[var(--text-primary)]">1 / {exam.questionCount}</p>
                </div>
              </div>
            </div>
          </Panel>

          <div className="grid gap-4 2xl:grid-cols-[0.8fr_1.2fr]">
            <div className="grid gap-4">
              <Panel className="border border-[var(--border-soft)] bg-[var(--surface-2)] p-6" tone="strong">
                <div className="flex flex-wrap items-center gap-3">
                  <Tag tone="warning">考试</Tag>
                  <Tag>{detail.algorithmTag}</Tag>
                  <Tag tone="accent">热度 {detail.heat}</Tag>
                </div>

                <h2 className="mt-4 text-xl font-semibold tracking-[-0.03em] text-[var(--text-primary)]">{detail.title}</h2>
                <div className="mt-5 space-y-4">
                  {detail.content.map((item) => (
                    <p key={item} className="text-sm leading-8 text-[var(--text-secondary)]">
                      {item}
                    </p>
                  ))}
                </div>
              </Panel>

              <JudgePanel questionId={questionId} examId={examId} submissions={submissions} />
            </div>

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
      </div>
    </AppShell>
  );
}
