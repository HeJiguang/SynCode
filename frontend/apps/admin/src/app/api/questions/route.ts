import { NextResponse } from "next/server";
import { requestJson, type ApiEnvelope, unwrapData } from "@aioj/api";

import { getAdminAccessToken } from "../../../lib/server-auth";

async function requireToken() {
  const token = await getAdminAccessToken();
  if (!token) {
    return NextResponse.json({ message: "管理员未登录。" }, { status: 401 });
  }
  return token;
}

export async function POST(request: Request) {
  const token = await requireToken();
  if (token instanceof NextResponse) return token;

  const body = await request.json();
  await requestJson<ApiEnvelope<null>>("/system/question/add", {
    method: "POST",
    token,
    body: JSON.stringify(body)
  }).then(unwrapData);

  return NextResponse.json({ ok: true });
}

export async function PUT(request: Request) {
  const token = await requireToken();
  if (token instanceof NextResponse) return token;

  const body = await request.json();
  await requestJson<ApiEnvelope<null>>("/system/question/edit", {
    method: "PUT",
    token,
    body: JSON.stringify(body)
  }).then(unwrapData);

  return NextResponse.json({ ok: true });
}

export async function DELETE(request: Request) {
  const token = await requireToken();
  if (token instanceof NextResponse) return token;

  const { searchParams } = new URL(request.url);
  const questionId = searchParams.get("questionId");
  if (!questionId) {
    return NextResponse.json({ message: "questionId 不能为空。" }, { status: 400 });
  }

  await requestJson<ApiEnvelope<null>>(`/system/question/delete?questionId=${encodeURIComponent(questionId)}`, {
    method: "DELETE",
    token
  }).then(unwrapData);

  return NextResponse.json({ ok: true });
}
