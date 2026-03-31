import * as React from "react";

import { AdminShell } from "../../../components/admin-shell";
import { AdminExamEditor } from "../../../components/admin-exam-editor";
import { getAdminExamDetail, getAdminProfile } from "../../../lib/admin-api";
import { requireAdminAccessToken } from "../../../lib/server-auth";

type AdminExamDetailPageProps = {
  params: Promise<{ examId: string }>;
};

export default async function AdminExamDetailPage({ params }: AdminExamDetailPageProps) {
  const { examId } = await params;
  const token = await requireAdminAccessToken();
  const [admin, exam] = await Promise.all([getAdminProfile(token), getAdminExamDetail(token, examId)]);

  return (
    <AdminShell
      adminName={admin.nickName}
      title="编辑考试"
      description="维护考试时间、题目绑定和发布状态。"
    >
      <AdminExamEditor exam={exam} />
    </AdminShell>
  );
}
