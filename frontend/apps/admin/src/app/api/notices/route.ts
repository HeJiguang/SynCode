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
  await requestJson<ApiEnvelope<null>>("/system/notice/add", {
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
  await requestJson<ApiEnvelope<null>>("/system/notice/edit", {
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
  const noticeId = searchParams.get("noticeId");
  if (!noticeId) {
    return NextResponse.json({ message: "noticeId 不能为空。" }, { status: 400 });
  }

  await requestJson<ApiEnvelope<null>>(`/system/notice/delete?noticeId=${encodeURIComponent(noticeId)}`, {
    method: "DELETE",
    token
  }).then(unwrapData);

  return NextResponse.json({ ok: true });
}
