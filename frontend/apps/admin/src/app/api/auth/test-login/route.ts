import { NextResponse } from "next/server";
import { requestJson, type ApiEnvelope, unwrapData } from "@aioj/api";
import { frontendTestLoginEnabled } from "@aioj/config";

import { ADMIN_ACCESS_TOKEN_COOKIE } from "../../../../lib/server-auth";

export async function POST(request: Request) {
  if (!frontendTestLoginEnabled || process.env.SYNCODE_TEST_LOGIN_ENABLED !== "true") {
    return NextResponse.json({ message: "测试账号登录未开启。" }, { status: 404 });
  }
  const body = (await request.json()) as { email?: string };
  const email = body.email?.trim();
  if (!email) return NextResponse.json({ message: "请输入测试教师邮箱。" }, { status: 400 });

  try {
    const payload = await requestJson<ApiEnvelope<string>>("/system/sysUser/test-login", {
      method: "POST",
      body: JSON.stringify({ email })
    });
    const token = unwrapData(payload);
    const response = NextResponse.json({ ok: true });
    response.cookies.set(ADMIN_ACCESS_TOKEN_COOKIE, token, {
      httpOnly: true,
      sameSite: "lax",
      path: "/admin"
    });
    return response;
  } catch (error) {
    return NextResponse.json({ message: error instanceof Error ? error.message : "测试账号登录失败。" }, { status: 401 });
  }
}
