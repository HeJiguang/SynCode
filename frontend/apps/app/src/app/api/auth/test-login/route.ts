import { NextResponse } from "next/server";

import { ACCESS_TOKEN_KEY, DEMO_SESSION_KEY, requestJson, unwrapData } from "@aioj/api";
import { frontendTestLoginEnabled } from "@aioj/config";
import { resolveApiRouteError } from "../../../../lib/api-route-error";

export async function POST(request: Request) {
  if (!frontendTestLoginEnabled || process.env.SYNCODE_TEST_LOGIN_ENABLED !== "true") {
    return NextResponse.json({ message: "测试账号登录未开启。" }, { status: 404 });
  }
  try {
    const body = await request.json();
    const payload = await requestJson<{ code: number; msg: string; data: string }>("/friend/user/test-login", {
      method: "POST",
      body: JSON.stringify({ email: body.email })
    });
    const token = unwrapData(payload);
    const response = NextResponse.json({ token });
    response.cookies.set(ACCESS_TOKEN_KEY, token, { httpOnly: true, sameSite: "lax", path: "/" });
    response.cookies.set(DEMO_SESSION_KEY, "", { maxAge: 0, path: "/" });
    return response;
  } catch (error) {
    const { status, body } = resolveApiRouteError(error, "测试账号登录失败。");
    return NextResponse.json(body, { status });
  }
}
