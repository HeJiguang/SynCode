import { NextResponse } from "next/server";

import { buildAuthHeaders, resolveBackendBaseUrl } from "@aioj/api";

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

  const headers = new Headers({ "Content-Type": "application/json" });
  for (const [key, value] of Object.entries(buildAuthHeaders(token))) {
    if (value) headers.set(key, value);
  }

  const upstream = await fetch(`${resolveBackendBaseUrl()}/ai/chat/stream`, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
    cache: "no-store"
  });

  if (!upstream.ok || !upstream.body) {
    const message = await upstream.text();
    return NextResponse.json({ message: message || "AI 流式响应失败。" }, { status: upstream.status || 500 });
  }

  return new Response(upstream.body, {
    status: upstream.status,
    headers: {
      "Content-Type": upstream.headers.get("content-type") ?? "text/event-stream; charset=utf-8",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive"
    }
  });
}
