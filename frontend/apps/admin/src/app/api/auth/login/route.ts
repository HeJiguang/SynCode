import { NextResponse } from "next/server";
import { requestJson, type ApiEnvelope, unwrapData } from "@aioj/api";

import { ADMIN_ACCESS_TOKEN_COOKIE } from "../../../../lib/server-auth";

type LoginBody = {
  userAccount?: string;
  password?: string;
};

export async function POST(request: Request) {
  const body = (await request.json()) as LoginBody;
  const userAccount = body.userAccount?.trim();
  const password = body.password?.trim();

  if (!userAccount || !password) {
    return NextResponse.json({ message: "管理员账号和密码不能为空。" }, { status: 400 });
  }

  const payload = await requestJson<ApiEnvelope<string>>("/system/sysUser/login", {
    method: "POST",
    body: JSON.stringify({ userAccount, password })
  });
  const token = unwrapData(payload);

  const response = NextResponse.json({ ok: true });
  response.cookies.set(ADMIN_ACCESS_TOKEN_COOKIE, token, {
    httpOnly: true,
    sameSite: "lax",
    path: "/admin"
  });
  return response;
}
