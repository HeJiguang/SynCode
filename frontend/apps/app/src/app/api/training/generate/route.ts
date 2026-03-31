import { NextResponse } from "next/server";

import type { ApiEnvelope } from "@aioj/api";
import { requestJson, unwrapData } from "@aioj/api";

import { getServerAccessToken } from "../../../../lib/server-auth";

type GenerateBody = {
  targetDirection?: string;
  preferredCount?: number;
  basedOnExamId?: number;
  sourceType?: string;
};

export async function POST(request: Request) {
  const token = await getServerAccessToken();
  if (!token) {
    return NextResponse.json({ message: "未登录，无法生成训练计划。" }, { status: 401 });
  }

  const body = (await request.json().catch(() => ({}))) as GenerateBody;
  const payload = await requestJson<ApiEnvelope<unknown>>("/friend/training/generate", {
    method: "POST",
    token,
    body: JSON.stringify({
      targetDirection: body.targetDirection?.trim() || undefined,
      preferredCount: body.preferredCount,
      basedOnExamId: body.basedOnExamId,
      sourceType: body.sourceType?.trim() || undefined
    })
  });

  return NextResponse.json(unwrapData(payload));
}
