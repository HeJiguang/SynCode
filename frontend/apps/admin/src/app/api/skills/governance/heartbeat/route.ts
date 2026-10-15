import { NextResponse } from "next/server";

import { getAdminAccessToken } from "../../../../../lib/server-auth";
import { governanceRequest } from "../../../../../lib/skill-governance";

export async function POST() {
  const token = await getAdminAccessToken();
  if (!token) return NextResponse.json({ message: "管理员未登录。" }, { status: 401 });
  try {
    const payload = await governanceRequest("/internal/skill-governance/heartbeat", {
      method: "POST",
      body: { min_distinct_owners: 3, neighbor_limit: 20 }
    });
    return NextResponse.json(payload);
  } catch (error) {
    return NextResponse.json({ message: error instanceof Error ? error.message : "治理心跳执行失败。" }, { status: 400 });
  }
}
