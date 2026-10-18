import { NextResponse } from "next/server";

import type { ApiEnvelope } from "@aioj/api";
import { requestJson, unwrapData } from "@aioj/api";

import { resolveApiRouteError } from "../../../../lib/api-route-error";
import { getServerAccessToken } from "../../../../lib/server-auth";

type GenerateBody = {
  prompt?: string;
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

  try {
    const body = (await request.json().catch(() => ({}))) as GenerateBody;
    const prompt = typeof body.prompt === "string" ? body.prompt.trim() : "";
    if (!prompt) {
      return NextResponse.json({ message: "请填写本轮训练诉求。" }, { status: 400 });
    }
    if (prompt.length > 1000) {
      return NextResponse.json({ message: "训练诉求不能超过 1000 个字符。" }, { status: 400 });
    }
    const payload = await requestJson<ApiEnvelope<unknown>>("/friend/training/generate", {
      method: "POST",
      token,
      body: JSON.stringify({
        prompt,
        targetDirection: body.targetDirection?.trim() || undefined,
        preferredCount: body.preferredCount,
        basedOnExamId: body.basedOnExamId,
        sourceType: body.sourceType?.trim() || undefined
      })
    });

    return NextResponse.json(unwrapData(payload));
  } catch (error) {
    const resolved = resolveApiRouteError(error, "生成训练计划失败。");
    return NextResponse.json(resolved.body, { status: resolved.status });
  }
}
