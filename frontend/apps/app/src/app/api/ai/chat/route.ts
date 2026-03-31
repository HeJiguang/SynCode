import { NextResponse } from "next/server";

import type { ApiEnvelope } from "@aioj/api";
import { requestJson, unwrapData } from "@aioj/api";

import { getServerAccessToken } from "../../../../lib/server-auth";

type AiChatBody = {
  questionTitle?: string;
  questionContent?: string;
  userCode?: string;
  judgeResult?: string;
  userMessage?: string;
};

export async function POST(request: Request) {
  const token = await getServerAccessToken();
  const body = (await request.json()) as AiChatBody;

  if (!body.userMessage?.trim()) {
    return NextResponse.json({ message: "AI 问题不能为空。" }, { status: 400 });
  }

  const payload = await requestJson<ApiEnvelope<string>>("/ai/chat", {
    method: "POST",
    token,
    body: JSON.stringify(body)
  });

  return NextResponse.json({ content: unwrapData(payload) });
}
