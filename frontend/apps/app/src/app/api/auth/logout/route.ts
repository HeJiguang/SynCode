import { NextResponse } from "next/server";
import { cookies } from "next/headers";

import { ACCESS_TOKEN_KEY, requestJson } from "@aioj/api";

export async function POST() {
  const cookieStore = await cookies();
  const token = cookieStore.get(ACCESS_TOKEN_KEY)?.value;

  if (token) {
    try {
      await requestJson("/friend/user/logout", {
        method: "DELETE",
        token
      });
    } catch {
      // Ignore backend logout failures and clear frontend session anyway.
    }
  }

  const response = NextResponse.json({ ok: true });
  response.cookies.set({
    name: ACCESS_TOKEN_KEY,
    value: "",
    maxAge: 0,
    path: "/"
  });
  return response;
}
