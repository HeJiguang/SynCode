import { NextResponse } from "next/server";
import { requestJson, type ApiEnvelope, unwrapData } from "@aioj/api";

import { getAdminAccessToken } from "../../../lib/server-auth";
import { resolveAdminApiError } from "../../../lib/api-route-error";

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

  try {
    const body = await request.json();
    const examId = await requestJson<ApiEnvelope<string>>("/system/exam/add", {
      method: "POST",
      token,
      body: JSON.stringify(body)
    }).then(unwrapData);
    return NextResponse.json({ ok: true, examId });
  } catch (error) {
    const resolved = resolveAdminApiError(error, "考试保存失败。");
    return NextResponse.json(resolved.body, { status: resolved.status });
  }
}

export async function PUT(request: Request) {
  const token = await requireToken();
  if (token instanceof NextResponse) return token;

  try {
    const body = await request.json();
    await requestJson<ApiEnvelope<null>>("/system/exam/edit", {
      method: "PUT",
      token,
      body: JSON.stringify(body)
    }).then(unwrapData);
    return NextResponse.json({ ok: true });
  } catch (error) {
    const resolved = resolveAdminApiError(error, "考试保存失败。");
    return NextResponse.json(resolved.body, { status: resolved.status });
  }
}

export async function DELETE(request: Request) {
  const token = await requireToken();
  if (token instanceof NextResponse) return token;

  const { searchParams } = new URL(request.url);
  const examId = searchParams.get("examId");
  if (!examId) {
    return NextResponse.json({ message: "examId 不能为空。" }, { status: 400 });
  }

  try {
    await requestJson<ApiEnvelope<null>>(`/system/exam/delete?examId=${encodeURIComponent(examId)}`, {
      method: "DELETE",
      token
    }).then(unwrapData);
    return NextResponse.json({ ok: true });
  } catch (error) {
    const resolved = resolveAdminApiError(error, "考试删除失败。");
    return NextResponse.json(resolved.body, { status: resolved.status });
  }
}
