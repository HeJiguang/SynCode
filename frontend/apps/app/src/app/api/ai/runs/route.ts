import { NextResponse } from "next/server";

import type { AiRunCreateResponse } from "@aioj/api";
import { requestJson } from "@aioj/api";

import { getServerAccessToken } from "../../../../lib/server-auth";


export async function POST(request: Request) {
  const token = await getServerAccessToken();
  const body = await request.json();

  if (!body?.context?.userMessage?.trim()) {
    return NextResponse.json({ message: "AI prompt is required." }, { status: 400 });
  }

  const payload = await requestJson<AiRunCreateResponse>("/api/runs", {
    method: "POST",
    token,
    body: JSON.stringify(body),
  });

  return NextResponse.json(payload);
}
