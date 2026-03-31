import * as React from "react";
import { getExamList, getPublicMessages } from "@aioj/api";
import { CalendarX2 } from "lucide-react";

import { AnnouncementCenter } from "../../components/announcement-center";
import { AppShell } from "../../components/app-shell";
import { appPublicPath } from "../../lib/paths";
import { getServerAccessToken } from "../../lib/server-auth";
import { Tag } from "@aioj/ui";

export default async function ExamsPage() {
  const token = await getServerAccessToken();
  const [exams, messages] = await Promise.all([getExamList(), getPublicMessages(token)]);

  return (
    <AppShell
      demoMode={!token}
      rail={<AnnouncementCenter messages={messages.slice(0, 2)} />}
    >
      {exams.length === 0 ? (
        <div className="flex flex-col items-center justify-center gap-5 py-24 text-center">
          <div className="flex h-16 w-16 items-center justify-center rounded-2xl border border-[var(--border-soft)] bg-[var(--surface-1)]">
            <CalendarX2 size={28} className="text-[var(--text-muted)]" />
          </div>
          <div className="space-y-2">
            <p className="text-lg font-semibold text-[var(--text-primary)]">暂时没有考试</p>
            <p className="text-sm leading-6 text-[var(--text-muted)]">
              当前没有正在进行或即将开始的考试，请稍后再来查看。
            </p>
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          {exams.map((exam) => (
            <a
              key={exam.examId}
              className="block rounded-[22px] border border-[var(--border-soft)] bg-[var(--surface-muted)] p-5 transition hover:border-[var(--border-strong)] hover:bg-[var(--surface-1)]"
              href={appPublicPath(`/exams/${exam.examId}`)}
            >
              <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                <div>
                  <div className="flex flex-wrap items-center gap-3">
                    <h3 className="text-xl font-semibold text-[var(--text-primary)]">{exam.title}</h3>
                    <Tag tone={exam.status === "已结束" ? "default" : exam.status === "进行中" ? "warning" : "accent"}>
                      {exam.status}
                    </Tag>
                  </div>
                  <p className="mt-3 text-sm text-[var(--text-secondary)]">
                    {exam.startTime} - {exam.endTime} · {exam.durationMinutes} 分钟 · {exam.questionCount} 题
                  </p>
                </div>
                <span className="text-sm text-[var(--text-muted)]">进入考试页</span>
              </div>
            </a>
          ))}
        </div>
      )}
    </AppShell>
  );
}
