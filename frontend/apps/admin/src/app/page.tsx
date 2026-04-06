import * as React from "react";

import { Panel, StatCard } from "@aioj/ui";

import { AdminShell } from "../components/admin-shell";
import { getAdminDashboardSummary, getAdminProfile } from "../lib/admin-api";
import { requireAdminAccessToken } from "../lib/server-auth";

export default async function AdminDashboardPage() {
  const token = await requireAdminAccessToken();
  const [admin, summary] = await Promise.all([
    getAdminProfile(token),
    getAdminDashboardSummary(token)
  ]);

  return (
    <AdminShell
      adminName={admin.nickName}
      title="后台总览"
      description="汇总当前系统规模，并保持核心运营入口清晰、稳定、可复核。"
    >
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard detail="按后端分页统计汇总的题目总数" label="题目数" value={String(summary.questionCount)} />
        <StatCard detail="按后端分页统计汇总的考试总数" label="考试数" value={String(summary.examCount)} />
        <StatCard detail="按后端分页统计汇总的公告总数" label="公告数" value={String(summary.noticeCount)} />
        <StatCard detail="按后端分页统计汇总的用户总数" label="用户数" value={String(summary.userCount)} />
      </div>
      <div className="grid gap-4 xl:grid-cols-[1.08fr_0.92fr]">
        <Panel className="p-5" tone="strong">
          <p className="kicker">当前重点</p>
          <h3 className="mt-2 text-xl font-semibold">运营焦点</h3>
          <div className="mt-5 space-y-3 text-sm leading-7 text-[var(--text-secondary)]">
            <p>用户端已经接入真实登录、真实题目详情、真实代码运行和异步判题链路。</p>
            <p>后台当前已经接入题目、考试、公告和用户四类核心维护能力，并直连真实后端契约。</p>
            <p>总览卡片直接读取后端分页元数据，不再从当前页行数据推算数量。</p>
          </div>
        </Panel>
        <Panel className="p-5">
          <p className="kicker">上线前检查</p>
          <h3 className="mt-2 text-xl font-semibold">待确认事项</h3>
          <div className="mt-5 space-y-3 text-sm leading-7 text-[var(--text-secondary)]">
            <p>核验公告新增、编辑、发布、置顶与撤回动作，确认真实持久化状态一致。</p>
            <p>串联检查题目编辑器的请求载荷、示例 JSON、默认代码和函数签名是否完整可用。</p>
            <p>确认考试时间、关联题目、发布流程和回滚行为仍然符合业务约束。</p>
          </div>
        </Panel>
      </div>
    </AdminShell>
  );
}
