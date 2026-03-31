import { NextResponse } from "next/server";

import type { ApiEnvelope } from "@aioj/api";
import { requestJson, unwrapData } from "@aioj/api";

import { getServerAccessToken } from "../../../../../lib/server-auth";

type FinishTaskBody = {
  taskId?: string | number;
  taskStatus?: number;
};

export async function POST(request: Request) {
  const token = await getServerAccessToken();
  if (!token) {
    return NextResponse.json({ message: "未登录，无法更新训练任务。" }, { status: 401 });
  }

  const body = (await request.json().catch(() => ({}))) as FinishTaskBody;
  if (!body.taskId) {
    return NextResponse.json({ message: "缺少 taskId。" }, { status: 400 });
  }

  await requestJson<ApiEnvelope<null>>("/friend/training/task/finish", {
    method: "POST",
    token,
    body: JSON.stringify({
      taskId: Number(body.taskId),
      taskStatus: body.taskStatus ?? 1
    })
  }).then(unwrapData);

  return NextResponse.json({ ok: true });
}
