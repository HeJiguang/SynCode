import { NextResponse } from "next/server";
import { requestJson, type ApiEnvelope, unwrapData } from "@aioj/api";

import { getAdminAccessToken } from "../../../../lib/server-auth";
import { resolveAdminApiError } from "../../../../lib/api-route-error";

export async function POST(request: Request) {
  const token = await getAdminAccessToken();
  if (!token) {
    return NextResponse.json({ message: "管理员未登录。" }, { status: 401 });
  }

  try {
    const body = await request.json();
    await requestJson<ApiEnvelope<null>>("/system/exam/question/add", {
      method: "POST",
      token,
      body: JSON.stringify(body)
    }).then(unwrapData);
    return NextResponse.json({ ok: true });
  } catch (error) {
    const resolved = resolveAdminApiError(error, "题目添加失败。");
    return NextResponse.json(resolved.body, { status: resolved.status });
  }
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

  try {
    await requestJson<ApiEnvelope<null>>(
      `/system/exam/question/delete?examId=${encodeURIComponent(examId)}&questionId=${encodeURIComponent(questionId)}`,
      { method: "DELETE", token }
    ).then(unwrapData);
    return NextResponse.json({ ok: true });
  } catch (error) {
    const resolved = resolveAdminApiError(error, "题目移除失败。");
    return NextResponse.json(resolved.body, { status: resolved.status });
  }
}

export async function PUT(request: Request) {
  const token = await getAdminAccessToken();
  if (!token) return NextResponse.json({ message: "管理员未登录。" }, { status: 401 });
  const body = (await request.json()) as { examId?: string; questions?: unknown[] };
  if (!body.examId) return NextResponse.json({ message: "examId 不能为空。" }, { status: 400 });
  try {
    await requestJson<ApiEnvelope<null>>(`/system/exam/${encodeURIComponent(body.examId)}/questions`, {
      method: "PUT",
      token,
      body: JSON.stringify({ questions: body.questions ?? [] })
    }).then(unwrapData);
    return NextResponse.json({ ok: true });
  } catch (error) {
    const resolved = resolveAdminApiError(error, "组卷保存失败。");
    return NextResponse.json(resolved.body, { status: resolved.status });
  }
}
