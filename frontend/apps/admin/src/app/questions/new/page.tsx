import * as React from "react";

import { AdminShell } from "../../../components/admin-shell";
import { AdminQuestionEditor } from "../../../components/admin-question-editor";
import { getAdminProfile } from "../../../lib/admin-api";
import { requireAdminAccessToken } from "../../../lib/server-auth";

export default async function AdminQuestionCreatePage() {
  const token = await requireAdminAccessToken();
  const admin = await getAdminProfile(token);

  return (
    <AdminShell
      adminName={admin.nickName}
      title="新增题目"
      description="直接创建真实题目，样例用例与默认代码会写入正式题库。"
    >
      <AdminQuestionEditor />
    </AdminShell>
  );
}
