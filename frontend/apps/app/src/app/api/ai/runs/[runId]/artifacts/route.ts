import { NextResponse } from "next/server";

import type { AiArtifact } from "@aioj/api";
import { requestJson } from "@aioj/api";

import { getServerAccessToken } from "../../../../../../lib/server-auth";


type RouteProps = {
  params: Promise<{ runId: string }>;
};

export async function GET(_request: Request, { params }: RouteProps) {
  const token = await getServerAccessToken();
  const { runId } = await params;

  const payload = await requestJson<AiArtifact[]>(`/api/runs/${encodeURIComponent(runId)}/artifacts`, {
    token,
  });

  return NextResponse.json(payload);
}
