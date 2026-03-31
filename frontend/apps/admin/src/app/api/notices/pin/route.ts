import { NextResponse } from "next/server";
import { requestJson, type ApiEnvelope, unwrapData } from "@aioj/api";

import { getAdminAccessToken } from "../../../../lib/server-auth";

export async function PUT(request: Request) {
  const token = await getAdminAccessToken();
  if (!token) {
    return NextResponse.json({ message: "管理员未登录。" }, { status: 401 });
  }

  const body = (await request.json()) as { noticeId?: string; pinned?: boolean };
  if (!body.noticeId) {
    return NextResponse.json({ message: "noticeId 不能为空。" }, { status: 400 });
  }

  await requestJson<ApiEnvelope<null>>(
    `/system/notice/pin?noticeId=${encodeURIComponent(body.noticeId)}&pinned=${body.pinned ? 1 : 0}`,
    {
      method: "PUT",
      token
    }
  ).then(unwrapData);

  return NextResponse.json({ ok: true });
}
