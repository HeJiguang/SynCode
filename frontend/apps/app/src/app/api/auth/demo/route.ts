import { NextResponse } from "next/server";

import { ACCESS_TOKEN_KEY, DEMO_SESSION_KEY } from "@aioj/api";

const DEMO_SESSION_MAX_AGE_SECONDS = 8 * 60 * 60;

export async function POST() {
  if (process.env.SYNCODE_DEMO_LOGIN_ENABLED !== "true") {
    return NextResponse.json({ message: "测试体验当前未开放。" }, { status: 404 });
  }

  const response = NextResponse.json({ ok: true });
  response.cookies.set({
    name: DEMO_SESSION_KEY,
    value: "1",
    httpOnly: true,
    sameSite: "lax",
    maxAge: DEMO_SESSION_MAX_AGE_SECONDS,
    path: "/"
  });
  response.cookies.set({
    name: ACCESS_TOKEN_KEY,
    value: "",
    maxAge: 0,
    path: "/"
  });
  return response;
}
