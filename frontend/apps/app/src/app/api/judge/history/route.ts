import { NextRequest, NextResponse } from "next/server";

import type { ApiEnvelope } from "@aioj/api";
import { requestJson, unwrapData } from "@aioj/api";

import { mapJudgeHistoryRow, type BackendSubmissionRow } from "../../../../lib/judge-history";
import { getServerAccessToken } from "../../../../lib/server-auth";

export async function GET(request: NextRequest) {
  const token = await getServerAccessToken();
  if (!token) {
    return NextResponse.json({ message: "鏈櫥褰曪紝鏃犳硶璇诲彇鎻愪氦璁板綍銆?" }, { status: 401 });
  }

  const questionId = request.nextUrl.searchParams.get("questionId");
  const examId = request.nextUrl.searchParams.get("examId");

  const params = new URLSearchParams();
  if (questionId && Number.isFinite(Number(questionId))) params.set("questionId", questionId);
  if (examId && Number.isFinite(Number(examId))) params.set("examId", examId);

  const query = params.toString();
  const payload = await requestJson<ApiEnvelope<BackendSubmissionRow[]>>(
    `/friend/user/question/submission/list${query ? `?${query}` : ""}`,
    { token }
  );

  return NextResponse.json(unwrapData(payload).map(mapJudgeHistoryRow));
}
