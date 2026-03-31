import * as React from "react";

import { AdminShell } from "../../../components/admin-shell";
import { AdminExamEditor } from "../../../components/admin-exam-editor";
import { getAdminProfile } from "../../../lib/admin-api";
import { requireAdminAccessToken } from "../../../lib/server-auth";

export default async function AdminExamCreatePage() {
  const token = await requireAdminAccessToken();
  const admin = await getAdminProfile(token);

  return (
    <AdminShell
      adminName={admin.nickName}
      title="新增考试"
      description="创建真实考试，保存后可继续关联题目并决定发布时间。"
    >
      <AdminExamEditor />
    </AdminShell>
  );
}
