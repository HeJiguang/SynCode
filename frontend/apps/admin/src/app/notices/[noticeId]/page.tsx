import * as React from "react";

import { AdminShell } from "../../../components/admin-shell";
import { AdminNoticeActions } from "../../../components/admin-notice-actions";
import { AdminNoticeEditor } from "../../../components/admin-notice-editor";
import { getAdminNoticeDetail, getAdminProfile } from "../../../lib/admin-api";
import { requireAdminAccessToken } from "../../../lib/server-auth";

type AdminNoticeDetailPageProps = {
  params: Promise<{ noticeId: string }>;
};

export default async function AdminNoticeDetailPage({ params }: AdminNoticeDetailPageProps) {
  const { noticeId } = await params;
  const token = await requireAdminAccessToken();
  const [admin, notice] = await Promise.all([getAdminProfile(token), getAdminNoticeDetail(token, noticeId)]);

  return (
    <AdminShell
      adminName={admin.nickName}
      title="编辑公告"
      description="这里维护单条公告的正文、发布状态和置顶状态。"
    >
      <AdminNoticeEditor notice={notice} />
      <AdminNoticeActions noticeId={noticeId} status={notice.status} isPinned={notice.isPinned} />
    </AdminShell>
  );
}
