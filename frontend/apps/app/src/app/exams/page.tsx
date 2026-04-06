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
      <section className="syncode-page-stack">
        <Panel className="syncode-page-hero overflow-hidden p-7 md:p-8" tone="strong">
          <div className="flex flex-col gap-8 xl:flex-row xl:items-end xl:justify-between">
            <div className="max-w-3xl">
              <p className="kicker">考试</p>
              <h1 className="mt-4 text-4xl font-semibold tracking-[-0.05em] text-[var(--text-primary)] md:text-5xl">考试安排</h1>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-[20px] border border-[var(--border-soft)] bg-[var(--surface-3)] p-4">
                <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--text-faint)]">总数</p>
                <p className="mt-3 text-2xl font-semibold text-[var(--text-primary)]">{exams.length}</p>
              </div>
              <div className="rounded-[20px] border border-[var(--border-soft)] bg-[var(--surface-3)] p-4">
                <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--text-faint)]">进行中</p>
                <p className="mt-3 text-2xl font-semibold text-[var(--text-primary)]">
                  {exams.filter((exam) => isActiveExam(exam.status)).length}
                </p>
              </div>
            </div>
          </div>
        </Panel>

        {exams.length === 0 ? (
          <Panel className="syncode-page-section flex flex-col items-center justify-center gap-5 p-12 text-center" tone="strong">
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl border border-[var(--border-soft)] bg-[var(--surface-1)]">
              <CalendarX2 size={28} className="text-[var(--text-muted)]" />
            </div>
            <div className="space-y-2">
                <p className="text-lg font-semibold text-[var(--text-primary)]">暂时没有考试安排</p>
            </div>
          </Panel>
        ) : (
          <div className="syncode-exam-list">
            {exams.map((exam) => (
              <a
                key={exam.examId}
                className="syncode-exam-entry block rounded-[18px] border border-[var(--border-soft)] bg-[var(--surface-2)] p-6 transition-all duration-300 ease-out hover:border-[var(--border-strong)] hover:bg-[var(--surface-3)]"
                href={appPublicPath(`/exams/${exam.examId}`)}
              >
                <div className="flex flex-col gap-6 xl:flex-row xl:items-center xl:justify-between">
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-3">
                      <h2 className="text-2xl font-semibold tracking-[-0.03em] text-[var(--text-primary)]">{exam.title}</h2>
                      <Tag tone={getExamTone(exam.status)}>{getExamStatusLabel(exam.status)}</Tag>
                    </div>

                    <div className="mt-5 grid gap-3 text-sm text-[var(--text-secondary)] md:grid-cols-3">
                      <div className="flex items-center gap-2 rounded-[16px] border border-[var(--border-soft)] bg-[var(--surface-3)] px-3 py-3">
                        <CalendarClock size={15} className="text-[var(--text-muted)]" />
                        <span>{exam.startTime}</span>
                      </div>
                      <div className="flex items-center gap-2 rounded-[16px] border border-[var(--border-soft)] bg-[var(--surface-3)] px-3 py-3">
                        <Clock3 size={15} className="text-[var(--text-muted)]" />
                        <span>{exam.durationMinutes} 分钟</span>
                      </div>
                      <div className="flex items-center gap-2 rounded-[16px] border border-[var(--border-soft)] bg-[var(--surface-3)] px-3 py-3">
                        <ListOrdered size={15} className="text-[var(--text-muted)]" />
                        <span>{exam.questionCount} 题</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center justify-between gap-4 rounded-[20px] border border-[var(--border-soft)] bg-[var(--surface-3)] px-4 py-4 xl:min-w-[220px] xl:flex-col xl:items-start">
                    <div className="flex items-center gap-2 text-sm font-medium text-[var(--text-primary)]">
                      <span>进入考试</span>
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
