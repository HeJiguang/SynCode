import * as React from "react";

import { AdminShell } from "../../../components/admin-shell";
import { AdminQuestionEditor } from "../../../components/admin-question-editor";
import { getAdminProfile, getAdminQuestionDetail } from "../../../lib/admin-api";
import { requireAdminAccessToken } from "../../../lib/server-auth";

type AdminQuestionDetailPageProps = {
  params: Promise<{ questionId: string }>;
};

export default async function AdminQuestionDetailPage({ params }: AdminQuestionDetailPageProps) {
  const { questionId } = await params;
  const token = await requireAdminAccessToken();
  const [admin, question] = await Promise.all([
    getAdminProfile(token),
    getAdminQuestionDetail(token, questionId)
  ]);

  return (
    <AdminShell
      adminName={admin.nickName}
      title="编辑题目"
      description="对真实题目进行编辑、删除和判题配置维护。"
    >
      <AdminQuestionEditor question={question} />
    </AdminShell>
  );
}
