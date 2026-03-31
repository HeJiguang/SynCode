import { NextResponse } from "next/server";

import { fetchLiveAiHistory } from "@aioj/api";

import { getServerAccessToken } from "../../../../lib/server-auth";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const questionId = searchParams.get("questionId");

  if (!questionId) {
    return NextResponse.json({ message: "questionId is required" }, { status: 400 });
  }

  const token = await getServerAccessToken();
  if (!token) {
    return NextResponse.json([]);
  }

  try {
    const messages = await fetchLiveAiHistory(questionId, token);
    return NextResponse.json(messages);
  } catch {
    return NextResponse.json([]);
  }
}
