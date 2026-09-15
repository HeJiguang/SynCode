import { NextResponse } from "next/server";
import { requestJson, type ApiEnvelope, unwrapData } from "@aioj/api";

import { getServerAccessToken } from "../../../../lib/server-auth";

type RouteContext = { params: Promise<{ segments: string[] }> };

async function proxy(request: Request, context: RouteContext, method: "GET" | "POST" | "PUT") {
  const token = await getServerAccessToken();
  if (!token) {
    return NextResponse.json({ message: "请先登录后进入考试。" }, { status: 401 });
  }
  const { segments } = await context.params;
  if (!segments?.length || segments.some((item) => !/^[a-zA-Z0-9-]+$/.test(item))) {
    return NextResponse.json({ message: "考试接口路径无效。" }, { status: 400 });
  }
  const sourceUrl = new URL(request.url);
  const path = `/friend/exam/${segments.join("/")}${sourceUrl.search}`;
  const headers: Record<string, string> = {};
  for (const name of ["idempotency-key", "x-request-id"]) {
    const value = request.headers.get(name);
    if (value) headers[name] = value;
  }
  const body = method === "GET" ? undefined : await request.text();
  try {
    const payload = await requestJson<ApiEnvelope<unknown>>(path, {
      method,
      token,
      headers,
      body: body || undefined
    });
    return NextResponse.json(unwrapData(payload));
  } catch (error) {
    return NextResponse.json(
      { message: error instanceof Error && error.message ? error.message : "考试服务暂不可用。" },
      { status: 400 }
    );
  }
}

export function GET(request: Request, context: RouteContext) {
  return proxy(request, context, "GET");
}

export function POST(request: Request, context: RouteContext) {
  return proxy(request, context, "POST");
}

export function PUT(request: Request, context: RouteContext) {
  return proxy(request, context, "PUT");
}
