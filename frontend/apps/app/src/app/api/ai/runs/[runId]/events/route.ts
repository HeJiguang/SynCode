import { NextResponse } from "next/server";

import { buildAuthHeaders } from "@aioj/api";

import { resolveAgentApiBaseUrl } from "../../../../../../lib/agent-base-url";
import { getServerAccessToken } from "../../../../../../lib/server-auth";

type RouteProps = {
  params: Promise<{ runId: string }>;
};

export async function GET(_request: Request, { params }: RouteProps) {
  const token = await getServerAccessToken();
  const { runId } = await params;
  const headers = new Headers();

  for (const [key, value] of Object.entries(buildAuthHeaders(token))) {
    if (value) headers.set(key, value);
  }

  const upstream = await fetch(`${resolveAgentApiBaseUrl()}/api/runs/${encodeURIComponent(runId)}/events`, {
    method: "GET",
    headers,
    cache: "no-store"
  });

  if (!upstream.ok || !upstream.body) {
    const message = await upstream.text();
    return NextResponse.json({ message: message || "Agent run event stream failed." }, { status: upstream.status || 500 });
  }

  return new Response(upstream.body, {
    status: upstream.status,
    headers: {
      "Content-Type": upstream.headers.get("content-type") ?? "text/event-stream; charset=utf-8",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive"
    }
  });
}
