import { NextResponse } from "next/server";

import { ACCESS_TOKEN_KEY, DEMO_SESSION_KEY, requestJson, unwrapData } from "@aioj/api";
import { resolveApiRouteError } from "../../../../lib/api-route-error";

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const payload = await requestJson<{ code: number; msg: string; data: string }>("/friend/user/code/login", {
      method: "POST",
      body: JSON.stringify(body)
    });

    const token = unwrapData(payload);
    const response = NextResponse.json({ token });
    response.cookies.set({
      name: ACCESS_TOKEN_KEY,
      value: token,
      httpOnly: true,
      sameSite: "lax",
      path: "/"
    });
    response.cookies.set({
      name: DEMO_SESSION_KEY,
      value: "",
      maxAge: 0,
      path: "/"
    });
    return response;
  } catch (error) {
    const { status, body } = resolveApiRouteError(error, "\u767b\u5f55\u5931\u8d25\u3002");
    return NextResponse.json(body, { status });
  }
}
