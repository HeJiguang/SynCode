import * as React from "react";

import { AdminShell } from "../../components/admin-shell";
import { Button, Panel, Tag } from "@aioj/ui";
import { getAdminProfile, getAdminQuestionRows } from "../../lib/admin-api";
import { requireAdminAccessToken } from "../../lib/server-auth";

export default async function AdminQuestionsPage() {
  const token = await requireAdminAccessToken();
  const [admin, questions] = await Promise.all([getAdminProfile(token), getAdminQuestionRows(token)]);

  return (
    <AdminShell
      adminName={admin.nickName}
      title="题目管理"
      description="题目管理以真实增删改为核心，页面直接围绕题面、样例、默认代码和判题约束展开。"
    >
      <Panel className="overflow-hidden">
        <div className="flex items-center justify-between border-b border-[var(--border-soft)] px-5 py-4">
          <h3 className="text-xl font-semibold">题目列表</h3>
          <a href="/admin/questions/new">
            <Button>新增题目</Button>
          </a>
        </div>
        <div className="divide-y divide-[var(--border-soft)]">
          {questions.map((item) => (
            <a
              key={item.questionId}
              href={`/admin/questions/${item.questionId}`}
              className="grid gap-3 px-5 py-4 transition hover:bg-[var(--surface-2)] md:grid-cols-[120px_minmax(0,1fr)_140px_180px] md:items-center"
            >
              <span className="text-sm text-[var(--text-muted)]">{item.questionId}</span>
              <span className="font-medium">{item.title}</span>
              <Tag tone={item.difficulty === "Easy" ? "success" : item.difficulty === "Medium" ? "warning" : "danger"}>
                {item.difficulty}
              </Tag>
              <span className="text-sm text-[var(--text-secondary)]">{item.updatedAt}</span>
            </a>
          ))}
        </div>
      </Panel>
    </AdminShell>
  );
}
