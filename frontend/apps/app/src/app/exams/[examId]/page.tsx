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
  description,
  message,
  icon
}: {
  title: string;
  description: string;
  message: string;
  icon: React.ReactNode;
}) {
  return (
    <AppShell>
      <Panel className="border border-white/10 bg-white/[0.03] p-8 backdrop-blur-md">
        <div className="flex items-start gap-4">
          <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-3 text-zinc-200">{icon}</div>
          <div className="space-y-2">
            <p className="kicker">Exam Workspace</p>
            <h1 className="text-2xl font-semibold text-zinc-50">{title}</h1>
            <p className="max-w-2xl text-sm leading-7 text-zinc-400">{description}</p>
            <p className="max-w-2xl text-sm leading-7 text-zinc-500">{message}</p>
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
        description="考试入口已经打开，但基础信息暂时没有成功返回。"
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
        description="当前考试已经同步，但没有可进入的首题。"
        message="请检查考试题目绑定和发布状态，确认首题已经成功配置后再重新进入考试工作区。"
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
        description="考试工作区已经打开，但当前题面和提交记录没有成功返回。"
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
          <Panel className="border border-white/10 bg-white/[0.03] p-6 backdrop-blur-md" tone="strong">
            <div className="flex flex-col gap-6 2xl:flex-row 2xl:items-end 2xl:justify-between">
              <div className="max-w-4xl">
                <div className="flex flex-wrap items-center gap-3">
                  <p className="kicker">Exam Workspace</p>
                  <Tag tone={getExamTone(exam.status)}>{getExamStatusLabel(exam.status)}</Tag>
                </div>
                <h1 className="mt-3 text-3xl font-semibold tracking-[-0.05em] text-zinc-50 md:text-4xl">{exam.title}</h1>
                <p className="mt-4 max-w-3xl text-sm leading-7 text-[var(--text-secondary)]">
                  当前工作区会把考试状态、时间范围、题面、代码编辑和判题反馈放在同一视图里，减少答题过程中的上下文切换。
                </p>
              </div>

              <div className="grid gap-3 md:grid-cols-4">
                <div className="rounded-[18px] border border-white/10 bg-white/[0.02] p-4 transition-all duration-300 ease-out hover:border-white/20 hover:bg-white/[0.04]">
                  <p className="flex items-center gap-2 text-sm text-zinc-500">
                    <ShieldCheck size={14} />
                    状态
                  </p>
                  <div className="mt-3">
                    <Tag tone={getExamTone(exam.status)}>{getExamStatusLabel(exam.status)}</Tag>
                  </div>
                </div>
                <div className="rounded-[18px] border border-white/10 bg-white/[0.02] p-4 transition-all duration-300 ease-out hover:border-white/20 hover:bg-white/[0.04]">
                  <p className="flex items-center gap-2 text-sm text-zinc-500">
                    <Clock3 size={14} />
                    时间区间
                  </p>
                  <p className="mt-3 text-sm font-medium leading-7 text-zinc-100">{exam.startTime} - {exam.endTime}</p>
                </div>
                <div className="rounded-[18px] border border-white/10 bg-white/[0.02] p-4 transition-all duration-300 ease-out hover:border-white/20 hover:bg-white/[0.04]">
                  <p className="flex items-center gap-2 text-sm text-zinc-500">
                    <TimerReset size={14} />
                    时长
                  </p>
                  <p className="mt-3 text-lg font-semibold text-zinc-50">{exam.durationMinutes} 分钟</p>
                </div>
                <div className="rounded-[18px] border border-white/10 bg-white/[0.02] p-4 transition-all duration-300 ease-out hover:border-white/20 hover:bg-white/[0.04]">
                  <p className="flex items-center gap-2 text-sm text-zinc-500">
                    <ListOrdered size={14} />
                    当前题号
                  </p>
                  <p className="mt-3 text-lg font-semibold text-zinc-50">1 / {exam.questionCount}</p>
                </div>
              </div>
            </div>
          </Panel>

          <div className="grid gap-4 2xl:grid-cols-[0.8fr_1.2fr]">
            <div className="grid gap-4">
              <Panel className="border border-white/10 bg-white/[0.03] p-6 backdrop-blur-md" tone="strong">
                <div className="flex flex-wrap items-center gap-3">
                  <Tag tone="warning">Exam</Tag>
                  <Tag>{detail.algorithmTag}</Tag>
                  <Tag tone="accent">Heat {detail.heat}</Tag>
                </div>

                <h2 className="mt-4 text-xl font-semibold tracking-[-0.03em] text-zinc-50">{detail.title}</h2>
                <div className="mt-5 space-y-4">
                  {detail.content.map((item) => (
                    <p key={item} className="text-sm leading-8 text-zinc-400">
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
