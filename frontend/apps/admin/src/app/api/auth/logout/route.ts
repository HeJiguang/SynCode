import { NextResponse } from "next/server";
import { requestJson, type ApiEnvelope } from "@aioj/api";

import { ADMIN_ACCESS_TOKEN_COOKIE } from "../../../../lib/server-auth";

export async function POST(request: Request) {
  const cookieHeader = request.headers.get("cookie") ?? "";
  const tokenMatch = cookieHeader.match(/syncode_admin_access_token=([^;]+)/);
  const token = tokenMatch?.[1];

  if (token) {
    try {
      await requestJson<ApiEnvelope<null>>("/system/sysUser/logout", {
        method: "DELETE",
        token
      });
    } catch {
      // ignore logout errors; local cookie cleanup is the primary requirement
    }
  }

  const response = NextResponse.redirect(new URL("/admin/login", request.url));
  response.cookies.set(ADMIN_ACCESS_TOKEN_COOKIE, "", {
    httpOnly: true,
    sameSite: "lax",
    path: "/admin",
    maxAge: 0
  });
  return response;
}
