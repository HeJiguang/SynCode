import * as React from "react";

import { AdminShell } from "../../../components/admin-shell";
import { AdminNoticeEditor } from "../../../components/admin-notice-editor";
import { getAdminProfile } from "../../../lib/admin-api";
import { requireAdminAccessToken } from "../../../lib/server-auth";

export default async function AdminNoticeCreatePage() {
  const token = await requireAdminAccessToken();
  const admin = await getAdminProfile(token);

  return (
    <AdminShell
      adminName={admin.nickName}
      title="新增公告"
      description="公告默认以草稿保存，确认内容无误后再发布。"
    >
      <AdminNoticeEditor />
    </AdminShell>
  );
}
