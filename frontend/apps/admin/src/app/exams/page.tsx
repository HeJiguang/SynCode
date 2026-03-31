import * as React from "react";

import { AdminShell } from "../../components/admin-shell";
import { Button, Panel, Tag } from "@aioj/ui";
import { getAdminExamRows, getAdminProfile } from "../../lib/admin-api";
import { requireAdminAccessToken } from "../../lib/server-auth";

export default async function AdminExamsPage() {
  const token = await requireAdminAccessToken();
  const [admin, exams] = await Promise.all([getAdminProfile(token), getAdminExamRows(token)]);

  return (
    <AdminShell
      adminName={admin.nickName}
      title="考试管理"
      description="考试管理页聚焦时间、发布状态和题目绑定，支持直接进入单场考试做真实维护。"
    >
      <Panel className="overflow-hidden">
        <div className="flex items-center justify-between border-b border-[var(--border-soft)] px-5 py-4">
          <h3 className="text-xl font-semibold">考试列表</h3>
          <a href="/admin/exams/new">
            <Button>新增考试</Button>
          </a>
        </div>
        <div className="divide-y divide-[var(--border-soft)]">
          {exams.map((item) => (
            <a
              key={item.examId}
              href={`/admin/exams/${item.examId}`}
              className="grid gap-3 px-5 py-4 transition hover:bg-[var(--surface-2)] md:grid-cols-[120px_minmax(0,1fr)_140px_200px_120px] md:items-center"
            >
              <span className="text-sm text-[var(--text-muted)]">{item.examId}</span>
              <span className="font-medium">{item.title}</span>
              <Tag tone={item.status === "已发布" ? "success" : "default"}>{item.status}</Tag>
              <span className="text-sm text-[var(--text-secondary)]">{item.startTime}</span>
              <span className="text-sm text-[var(--text-secondary)]">{item.participantCount}</span>
            </a>
          ))}
        </div>
      </Panel>
    </AdminShell>
  );
}
