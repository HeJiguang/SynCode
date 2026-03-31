import { NextResponse } from "next/server";
import { requestJson, type ApiEnvelope, unwrapData } from "@aioj/api";

import { getAdminAccessToken } from "../../../../lib/server-auth";

export async function PUT(request: Request) {
  const token = await getAdminAccessToken();
  if (!token) {
    return NextResponse.json({ message: "管理员未登录。" }, { status: 401 });
  }

  const body = (await request.json()) as { examId?: string; publish?: boolean };
  if (!body.examId) {
    return NextResponse.json({ message: "examId 不能为空。" }, { status: 400 });
  }

  const path = body.publish
    ? `/system/exam/publish?examId=${encodeURIComponent(body.examId)}`
    : `/system/exam/cancelPublish?examId=${encodeURIComponent(body.examId)}`;

  await requestJson<ApiEnvelope<null>>(path, {
    method: "PUT",
    token
  }).then(unwrapData);

  return NextResponse.json({ ok: true });
}
