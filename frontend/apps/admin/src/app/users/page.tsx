import * as React from "react";

import { AdminShell } from "../../components/admin-shell";
import { AdminUserStatusToggle } from "../../components/admin-user-status-toggle";
import { Panel, Tag } from "@aioj/ui";
import { getAdminProfile, getAdminUserRows } from "../../lib/admin-api";
import { requireAdminAccessToken } from "../../lib/server-auth";

export default async function AdminUsersPage() {
  const token = await requireAdminAccessToken();
  const [admin, users] = await Promise.all([getAdminProfile(token), getAdminUserRows(token)]);

  return (
    <AdminShell
      adminName={admin.nickName}
      title="用户管理"
      description="用户管理页重点展示状态、邮箱和方向信息，并提供最基础的冻结/恢复操作。"
    >
      <Panel className="overflow-hidden">
        <div className="border-b border-[var(--border-soft)] px-5 py-4">
          <h3 className="text-xl font-semibold">用户列表</h3>
        </div>
        <div className="divide-y divide-[var(--border-soft)]">
          {users.map((item) => (
            <div key={item.userId} className="grid gap-3 px-5 py-4 md:grid-cols-[120px_1fr_1fr_120px_220px_100px] md:items-center">
              <span className="text-sm text-[var(--text-muted)]">{item.userId}</span>
              <span className="font-medium">{item.nickName}</span>
              <span className="text-sm text-[var(--text-secondary)]">{item.email}</span>
              <Tag tone={item.status === "正常" ? "success" : "danger"}>{item.status}</Tag>
              <span className="text-sm text-[var(--text-secondary)]">{item.direction}</span>
              <AdminUserStatusToggle userId={item.userId} status={item.status} />
            </div>
          ))}
        </div>
      </Panel>
    </AdminShell>
  );
}
