import { NextRequest, NextResponse } from "next/server";

import type { ApiEnvelope } from "@aioj/api";
import { requestJson, unwrapData } from "@aioj/api";

import { normalizeJudgeOutcome } from "../../../../lib/judge-result";
import { buildJudgeResultParams } from "../../../../lib/judge-route-contracts";
import { getServerAccessToken } from "../../../../lib/server-auth";

type BackendJudgeResult = {
  pass?: number | null;
  exeMessage?: string | null;
  useTime?: number | null;
  useMemory?: number | null;
};

export async function GET(request: NextRequest) {
  const token = await getServerAccessToken();
  if (!token) {
    return NextResponse.json({ message: "未登录，无法查询判题结果。" }, { status: 401 });
  }

  const questionId = request.nextUrl.searchParams.get("questionId");
  const requestId = request.nextUrl.searchParams.get("requestId");
  const examId = request.nextUrl.searchParams.get("examId");

  if (!requestId) {
    return NextResponse.json({ message: "requestId 不能为空。" }, { status: 400 });
  }

  const params = questionId ? buildJudgeResultParams(questionId, requestId, examId) : null;
  if (!params) {
    return NextResponse.json({ message: "questionId 必须是数字 ID。" }, { status: 400 });
  }

  const payload = await requestJson<ApiEnvelope<BackendJudgeResult>>(
    `/friend/user/question/exe/result?${params.toString()}`,
    { token }
  );

  return NextResponse.json(normalizeJudgeOutcome({ requestId, ...unwrapData(payload) }));
}
