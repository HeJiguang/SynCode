import * as React from "react";
import { ArrowRight, CalendarClock, CalendarX2, Clock3, ListOrdered } from "lucide-react";
import { getExamList, getPublicMessages } from "@aioj/api";

import { AnnouncementCenter } from "../../components/announcement-center";
import { AppShell } from "../../components/app-shell";
import { appPublicPath } from "../../lib/paths";
import { getServerAccessToken } from "../../lib/server-auth";
import { Panel, Tag } from "@aioj/ui";

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

function getExamStatusSummary(status: string) {
  if (status === ACTIVE_STATUS) return "当前可以进入考试工作区并开始答题。";
  if (status === FINISHED_STATUS) return "考试已经结束，可用于回顾已完成的安排。";
  return "考试尚未开始，先确认时间安排与题目数量。";
}

function isActiveExam(status: string) {
  return getExamStatusLabel(status) === "进行中";
}

export default async function ExamsPage() {
  const token = await getServerAccessToken();
  const [exams, messages] = await Promise.all([getExamList(), getPublicMessages(token)]);

  return (
    <AppShell
      demoMode={!token}
      rail={<AnnouncementCenter messages={messages.slice(0, 2)} />}
    >
      <section className="space-y-6">
        <Panel className="overflow-hidden p-7 md:p-8" tone="accent">
          <div className="flex flex-col gap-8 xl:flex-row xl:items-end xl:justify-between">
            <div className="max-w-3xl">
              <p className="kicker">Exam Center</p>
              <h1 className="mt-4 text-4xl font-semibold tracking-[-0.05em] text-zinc-50 md:text-5xl">
                考试安排与进入入口
              </h1>
              <p className="mt-5 max-w-2xl text-sm leading-8 text-[var(--text-secondary)] md:text-base">
                这里聚合当前开放、即将开始和已结束的考试安排。进入考试前，先确认时间窗口、题目数量和考试状态，避免在切换页面时丢失上下文。
              </p>
            </div>

            <div className="grid gap-3 sm:grid-cols-3">
              <div className="rounded-[20px] border border-white/10 bg-white/[0.03] p-4 backdrop-blur-md">
                <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--text-faint)]">Schedule</p>
                <p className="mt-3 text-2xl font-semibold text-zinc-50">{exams.length}</p>
                <p className="mt-1 text-sm text-[var(--text-secondary)]">已同步的考试安排</p>
              </div>
              <div className="rounded-[20px] border border-white/10 bg-white/[0.03] p-4 backdrop-blur-md">
                <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--text-faint)]">Status</p>
                <p className="mt-3 text-2xl font-semibold text-zinc-50">
                  {exams.filter((exam) => isActiveExam(exam.status)).length}
                </p>
                <p className="mt-1 text-sm text-[var(--text-secondary)]">当前进行中的考试</p>
              </div>
              <div className="rounded-[20px] border border-white/10 bg-white/[0.03] p-4 backdrop-blur-md">
                <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--text-faint)]">Access</p>
                <p className="mt-3 text-2xl font-semibold text-zinc-50">/app/exams</p>
                <p className="mt-1 text-sm text-[var(--text-secondary)]">统一进入考试工作区</p>
              </div>
            </div>
          </div>
        </Panel>

        {exams.length === 0 ? (
          <Panel className="flex flex-col items-center justify-center gap-5 p-12 text-center" tone="strong">
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl border border-[var(--border-soft)] bg-[var(--surface-1)]">
              <CalendarX2 size={28} className="text-[var(--text-muted)]" />
            </div>
            <div className="space-y-2">
              <p className="text-lg font-semibold text-[var(--text-primary)]">暂时没有考试安排</p>
              <p className="text-sm leading-7 text-[var(--text-muted)]">
                当前没有正在进行或即将开始的考试。你可以先继续训练主线，稍后再回来查看新的考试计划。
              </p>
            </div>
          </Panel>
        ) : (
          <div className="space-y-4">
            {exams.map((exam) => (
              <a
                key={exam.examId}
                className="block rounded-[24px] border border-white/10 bg-white/[0.02] p-6 backdrop-blur-md transition-all duration-300 ease-out hover:border-white/20 hover:bg-white/[0.04]"
                href={appPublicPath(`/exams/${exam.examId}`)}
              >
                <div className="flex flex-col gap-6 xl:flex-row xl:items-center xl:justify-between">
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-3">
                      <h2 className="text-2xl font-semibold tracking-[-0.03em] text-zinc-50">{exam.title}</h2>
                      <Tag tone={getExamTone(exam.status)}>{getExamStatusLabel(exam.status)}</Tag>
                    </div>
                    <p className="mt-3 max-w-2xl text-sm leading-7 text-[var(--text-secondary)]">{getExamStatusSummary(exam.status)}</p>

                    <div className="mt-5 grid gap-3 text-sm text-[var(--text-secondary)] md:grid-cols-3">
                      <div className="flex items-center gap-2 rounded-[16px] border border-white/10 bg-white/[0.03] px-3 py-3">
                        <CalendarClock size={15} className="text-[var(--text-muted)]" />
                        <span>{exam.startTime}</span>
                      </div>
                      <div className="flex items-center gap-2 rounded-[16px] border border-white/10 bg-white/[0.03] px-3 py-3">
                        <Clock3 size={15} className="text-[var(--text-muted)]" />
                        <span>{exam.durationMinutes} 分钟</span>
                      </div>
                      <div className="flex items-center gap-2 rounded-[16px] border border-white/10 bg-white/[0.03] px-3 py-3">
                        <ListOrdered size={15} className="text-[var(--text-muted)]" />
                        <span>{exam.questionCount} 题</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center justify-between gap-4 rounded-[20px] border border-white/10 bg-white/[0.03] px-4 py-4 xl:min-w-[220px] xl:flex-col xl:items-start">
                    <div>
                      <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--text-faint)]">Workspace</p>
                      <p className="mt-2 text-sm leading-7 text-[var(--text-secondary)]">进入考试页，查看题面、提交记录和实时判题状态。</p>
                    </div>
                    <div className="flex items-center gap-2 text-sm font-medium text-zinc-100">
                      <span>进入考试页</span>
                      <ArrowRight size={15} />
                    </div>
                  </div>
                </div>
              </a>
            ))}
          </div>
        )}
      </section>
    </AppShell>
  );
}
