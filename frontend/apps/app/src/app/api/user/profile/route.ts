import { NextResponse } from "next/server";

import type { ApiEnvelope } from "@aioj/api";
import { requestJson, unwrapData } from "@aioj/api";

import { getServerAccessToken } from "../../../../lib/server-auth";

type UpdateProfileBody = {
  nickName?: string;
  email?: string;
  schoolName?: string;
  majorName?: string;
  introduce?: string;
};

export async function PUT(request: Request) {
  const token = await getServerAccessToken();
  if (!token) {
    return NextResponse.json({ message: "未登录，无法更新个人资料。" }, { status: 401 });
  }

  const body = (await request.json()) as UpdateProfileBody;
  await requestJson<ApiEnvelope<null>>("/friend/user/edit", {
    method: "PUT",
    token,
    body: JSON.stringify({
      nickName: body.nickName?.trim() || undefined,
      email: body.email?.trim() || undefined,
      schoolName: body.schoolName?.trim() || undefined,
      majorName: body.majorName?.trim() || undefined,
      introduce: body.introduce?.trim() || undefined
    })
  }).then(unwrapData);

  return NextResponse.json({ ok: true });
}
