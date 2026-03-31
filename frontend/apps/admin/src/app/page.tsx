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
      title="Admin Overview"
      description="Track the current system totals and keep the core operator entry points stable, explicit, and reviewable."
    >
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard detail="Total managed problems from backend pagination totals" label="Problems" value={String(summary.questionCount)} />
        <StatCard detail="Total exams from backend pagination totals" label="Exams" value={String(summary.examCount)} />
        <StatCard detail="Total notices from backend pagination totals" label="Notices" value={String(summary.noticeCount)} />
        <StatCard detail="Total users from backend pagination totals" label="Users" value={String(summary.userCount)} />
      </div>
      <div className="grid gap-4 xl:grid-cols-[1.08fr_0.92fr]">
        <Panel className="p-5" tone="strong">
          <p className="kicker">Operations</p>
          <h3 className="mt-2 text-xl font-semibold">Current focus</h3>
          <div className="mt-5 space-y-3 text-sm leading-7 text-[var(--text-secondary)]">
            <p>The user app already routes through real login, real problem detail, real code run, and async judge flows.</p>
            <p>The admin app now exposes question, exam, notice, and user maintenance against live backend contracts.</p>
            <p>The dashboard totals are read from backend pagination metadata instead of inferring counts from the current page rows.</p>
          </div>
        </Panel>
        <Panel className="p-5">
          <p className="kicker">Next Steps</p>
          <h3 className="mt-2 text-xl font-semibold">Pre-release checks</h3>
          <div className="mt-5 space-y-3 text-sm leading-7 text-[var(--text-secondary)]">
            <p>Validate notice add, edit, publish, pin, and rollback actions against real persisted state.</p>
            <p>Review problem editor payloads, sample JSON, starter code, and function signatures end to end.</p>
            <p>Confirm exam time, linked questions, publish flow, and rollback behavior still respect business constraints.</p>
          </div>
        </Panel>
      </div>
    </AdminShell>
  );
}
