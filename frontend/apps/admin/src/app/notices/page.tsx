import * as React from "react";

import { AdminShell } from "../../components/admin-shell";
import { Button, Panel, Tag } from "@aioj/ui";
import { getAdminNoticeRows, getAdminProfile } from "../../lib/admin-api";
import { requireAdminAccessToken } from "../../lib/server-auth";

export default async function AdminNoticesPage() {
  const token = await requireAdminAccessToken();
  const [admin, notices] = await Promise.all([getAdminProfile(token), getAdminNoticeRows(token)]);

  return (
    <AdminShell
      adminName={admin.nickName}
      title="公告管理"
      description="公告系统已经切到独立的 `tb_notice`，这里负责真实的新增、编辑、发布、置顶和撤回。"
    >
      <Panel className="overflow-hidden">
        <div className="flex items-center justify-between border-b border-[var(--border-soft)] px-5 py-4">
          <h3 className="text-xl font-semibold">公告列表</h3>
          <a href="/admin/notices/new">
            <Button>新增公告</Button>
          </a>
        </div>
        <div className="divide-y divide-[var(--border-soft)]">
          {notices.map((item) => (
            <a
              key={item.noticeId}
              href={`/admin/notices/${item.noticeId}`}
              className="grid gap-3 px-5 py-4 transition hover:bg-[var(--surface-2)] md:grid-cols-[120px_minmax(0,1fr)_120px_120px_180px_140px] md:items-center"
            >
              <span className="text-sm text-[var(--text-muted)]">{item.noticeId}</span>
              <div>
                <p className="font-medium text-[var(--text-primary)]">{item.title}</p>
                <p className="mt-1 text-xs text-[var(--text-muted)]">{item.createName}</p>
              </div>
              <Tag tone={item.statusLabel === "已发布" ? "success" : "default"}>{item.statusLabel}</Tag>
              <Tag tone={item.pinned ? "accent" : "default"}>{item.pinned ? "置顶" : "普通"}</Tag>
              <span className="text-sm text-[var(--text-secondary)]">{item.publishTime}</span>
              <span className="text-sm text-[var(--text-secondary)]">{item.isPublic ? "公开" : "内部"}</span>
            </a>
          ))}
        </div>
      </Panel>
    </AdminShell>
  );
}
