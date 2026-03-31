import { NextResponse } from "next/server";
import { requestJson, type ApiEnvelope, unwrapData } from "@aioj/api";

import { getAdminAccessToken } from "../../../../lib/server-auth";

export async function PUT(request: Request) {
  const token = await getAdminAccessToken();
  if (!token) {
    return NextResponse.json({ message: "管理员未登录。" }, { status: 401 });
  }

  const body = (await request.json()) as { noticeId?: string; publish?: boolean };
  if (!body.noticeId) {
    return NextResponse.json({ message: "noticeId 不能为空。" }, { status: 400 });
  }

  const path = body.publish
    ? `/system/notice/publish?noticeId=${encodeURIComponent(body.noticeId)}`
    : `/system/notice/cancelPublish?noticeId=${encodeURIComponent(body.noticeId)}`;

  await requestJson<ApiEnvelope<null>>(path, {
    method: "PUT",
    token
  }).then(unwrapData);

  return NextResponse.json({ ok: true });
}
