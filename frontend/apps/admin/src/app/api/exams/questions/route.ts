import { NextResponse } from "next/server";
import { requestJson, type ApiEnvelope, unwrapData } from "@aioj/api";

import { getAdminAccessToken } from "../../../../lib/server-auth";

export async function POST(request: Request) {
  const token = await getAdminAccessToken();
  if (!token) {
    return NextResponse.json({ message: "管理员未登录。" }, { status: 401 });
  }

  const body = await request.json();
  await requestJson<ApiEnvelope<null>>("/system/exam/question/add", {
    method: "POST",
    token,
    body: JSON.stringify(body)
  }).then(unwrapData);

  return NextResponse.json({ ok: true });
}

export async function DELETE(request: Request) {
  const token = await getAdminAccessToken();
  if (!token) {
    return NextResponse.json({ message: "管理员未登录。" }, { status: 401 });
  }

  const { searchParams } = new URL(request.url);
  const examId = searchParams.get("examId");
  const questionId = searchParams.get("questionId");
  if (!examId || !questionId) {
    return NextResponse.json({ message: "examId 和 questionId 不能为空。" }, { status: 400 });
  }

  await requestJson<ApiEnvelope<null>>(
    `/system/exam/question/delete?examId=${encodeURIComponent(examId)}&questionId=${encodeURIComponent(questionId)}`,
    {
      method: "DELETE",
      token
    }
  ).then(unwrapData);

  return NextResponse.json({ ok: true });
}
