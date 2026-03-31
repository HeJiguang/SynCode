import { NextResponse } from "next/server";

import { requestJson, unwrapData } from "@aioj/api";

export async function POST(request: Request) {
  const body = await request.json();
  const payload = await requestJson<{ code: number; msg: string; data: null }>("/friend/user/sendCode", {
    method: "POST",
    body: JSON.stringify(body)
  });

  unwrapData(payload);
  return NextResponse.json({ ok: true });
}
