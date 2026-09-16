import { NextResponse } from "next/server";
import { requestJson, type ApiEnvelope, unwrapData } from "@aioj/api";

import { getAdminAccessToken } from "../../../../lib/server-auth";
import { resolveAdminApiError } from "../../../../lib/api-route-error";

export async function PUT(request: Request) {
  const token = await getAdminAccessToken();
  if (!token) {
    return NextResponse.json({ message: "管理员未登录。" }, { status: 401 });
  }

  try {
    const body = await request.json();
    await requestJson<ApiEnvelope<null>>("/system/user/updateStatus", {
      method: "PUT",
      token,
      body: JSON.stringify(body)
    }).then(unwrapData);
    return NextResponse.json({ ok: true });
  } catch (error) {
    const resolved = resolveAdminApiError(error, "用户状态更新失败。");
    return NextResponse.json(resolved.body, { status: resolved.status });
  }
}
