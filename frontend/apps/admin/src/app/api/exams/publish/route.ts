import { NextResponse } from "next/server";
import { requestJson, type ApiEnvelope, unwrapData } from "@aioj/api";

import { getAdminAccessToken } from "../../../../lib/server-auth";
import { resolveAdminApiError } from "../../../../lib/api-route-error";

export async function PUT(request: Request) {
  const token = await getAdminAccessToken();
  if (!token) {
    return NextResponse.json({ message: "管理员未登录。" }, { status: 401 });
  }

  const body = (await request.json().catch(() => ({}))) as { examId?: string; publish?: boolean };
  if (!body.examId) {
    return NextResponse.json({ message: "examId 不能为空。" }, { status: 400 });
  }

  const path = body.publish
    ? `/system/exam/${encodeURIComponent(body.examId)}/publish`
    : `/system/exam/${encodeURIComponent(body.examId)}/withdraw`;

  try {
    await requestJson<ApiEnvelope<null>>(path, {
      method: "POST",
      token,
      headers: body.publish ? { "Idempotency-Key": `publish-${crypto.randomUUID()}` } : undefined
    }).then(unwrapData);
  } catch (error) {
    const resolved = resolveAdminApiError(error, "考试状态更新失败。");
    return NextResponse.json(resolved.body, { status: resolved.status });
  }

  return NextResponse.json({ ok: true });
}
