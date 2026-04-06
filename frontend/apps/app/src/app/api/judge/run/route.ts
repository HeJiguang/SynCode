import { NextResponse } from "next/server";

import {
  type ApiEnvelope,
  type CodeLanguage,
  isJudgeLanguageSupported,
  programTypeFromLanguage,
  requestJson,
  unwrapData
} from "@aioj/api";

import { buildJudgeRunPayload } from "../../../../lib/judge-route-contracts";
import { getServerAccessToken } from "../../../../lib/server-auth";

type RunBody = {
  questionId?: string;
  examId?: string | null;
  language?: CodeLanguage;
  code?: string;
  customInputs?: string[];
};

type RunCaseResult = {
  input?: string;
  expectedOutput?: string | null;
  actualOutput?: string | null;
  passed?: boolean | null;
  custom?: boolean | null;
};

type RunResponse = {
  runStatus?: string;
  exeMessage?: string;
  useMemory?: number | null;
  useTime?: number | null;
  caseResults?: RunCaseResult[];
};

export async function POST(request: Request) {
  const token = await getServerAccessToken();
  if (!token) {
    return NextResponse.json({ message: "未登录，无法运行代码。" }, { status: 401 });
  }

  const body = (await request.json()) as RunBody;
  const language = body.language;
  const code = body.code?.trim();

  if (!language || !isJudgeLanguageSupported(language)) {
    return NextResponse.json({ message: "当前真实运行仅支持 Java。" }, { status: 400 });
  }
  if (!code) {
    return NextResponse.json({ message: "运行代码不能为空。" }, { status: 400 });
  }

  const payloadBody = buildJudgeRunPayload(body, programTypeFromLanguage(language), code);
  if (!payloadBody) {
    return NextResponse.json({ message: "questionId 必须是后端可识别的数字 ID。" }, { status: 400 });
  }

  const payload = await requestJson<ApiEnvelope<RunResponse>>("/friend/user/question/run", {
    method: "POST",
    token,
    body: JSON.stringify(payloadBody)
  });

  return NextResponse.json(unwrapData(payload));
}
