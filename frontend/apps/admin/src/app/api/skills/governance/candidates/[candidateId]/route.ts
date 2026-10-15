import { NextResponse } from "next/server";

import { getAdminProfile } from "../../../../../../lib/admin-api";
import { getAdminAccessToken } from "../../../../../../lib/server-auth";
import { governanceRequest } from "../../../../../../lib/skill-governance";

type RouteContext = { params: Promise<{ candidateId: string }> };

export async function POST(request: Request, context: RouteContext) {
  const token = await getAdminAccessToken();
  if (!token) return NextResponse.json({ message: "管理员未登录。" }, { status: 401 });
  try {
    const { candidateId } = await context.params;
    if (!/^[a-f0-9]{64}$/.test(candidateId)) {
      return NextResponse.json({ message: "候选 ID 无效。" }, { status: 400 });
    }
    const body = await request.json() as {
      decision?: "approve" | "reject";
      note?: string;
      proposed_skill_name?: string;
      category?: string;
      content?: string;
    };
    const admin = await getAdminProfile(token);
    const payload = await governanceRequest(
      `/internal/skill-governance/candidates/${candidateId}/review`,
      {
        method: "POST",
        body: { ...body, reviewer: admin.userAccount ?? admin.nickName }
      }
    );
    return NextResponse.json(payload);
  } catch (error) {
    return NextResponse.json({ message: error instanceof Error ? error.message : "候选审核失败。" }, { status: 400 });
  }
}
