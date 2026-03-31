import { NextResponse } from "next/server";

import {
  type ApiEnvelope,
  type CodeLanguage,
  isJudgeLanguageSupported,
  programTypeFromLanguage,
  requestJson,
  unwrapData
} from "@aioj/api";

import { getServerAccessToken } from "../../../../lib/server-auth";

type SubmitBody = {
  questionId?: string;
  examId?: string | null;
  language?: CodeLanguage;
  code?: string;
};

type AsyncSubmitResponse = {
  requestId: string;
  status: string;
};

export async function POST(request: Request) {
  const token = await getServerAccessToken();
  if (!token) {
    return NextResponse.json({ message: "未登录，无法提交判题。" }, { status: 401 });
  }

  const body = (await request.json()) as SubmitBody;
  const questionId = Number(body.questionId);
  const examId = body.examId ? Number(body.examId) : undefined;
  const language = body.language;
  const code = body.code?.trim();

  if (!Number.isFinite(questionId)) {
    return NextResponse.json({ message: "questionId 必须是后端可识别的数字 ID。" }, { status: 400 });
  }
  if (!language || !isJudgeLanguageSupported(language)) {
    return NextResponse.json({ message: "当前真实判题仅支持 Java。" }, { status: 400 });
  }
  if (!code) {
    return NextResponse.json({ message: "提交代码不能为空。" }, { status: 400 });
  }

  const payload = await requestJson<ApiEnvelope<AsyncSubmitResponse>>("/friend/user/question/rabbit/submit", {
    method: "POST",
    token,
    body: JSON.stringify({
      questionId,
      examId: Number.isFinite(examId) ? examId : undefined,
      programType: programTypeFromLanguage(language),
      userCode: code
    })
  });

  return NextResponse.json(unwrapData(payload));
}
