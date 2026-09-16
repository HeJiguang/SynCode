import { NextResponse } from "next/server";
import { requestJson, type ApiEnvelope, unwrapData } from "@aioj/api";

import { getAdminAccessToken } from "../../../../lib/server-auth";

type RouteContext = { params: Promise<{ segments: string[] }> };
type Method = "GET" | "POST" | "PUT" | "DELETE";

async function proxy(request: Request, context: RouteContext, method: Method) {
  const token = await getAdminAccessToken();
  if (!token) return NextResponse.json({ message: "管理员未登录。" }, { status: 401 });
  const { segments } = await context.params;
  if (!segments?.length || segments.some((item) => !/^[a-zA-Z0-9-]+$/.test(item))) {
    return NextResponse.json({ message: "考试接口路径无效。" }, { status: 400 });
  }
  const headers: Record<string, string> = {};
  for (const name of ["idempotency-key", "x-request-id"]) {
    const value = request.headers.get(name);
    if (value) headers[name] = value;
  }
  const body = method === "GET" ? undefined : await request.text();
  try {
    const payload = await requestJson<ApiEnvelope<unknown>>(`/system/exam/${segments.join("/")}`, {
      method,
      token,
      headers,
      body: body || undefined
    });
    return NextResponse.json(unwrapData(payload));
  } catch (error) {
    return NextResponse.json({ message: error instanceof Error ? error.message : "考试操作失败。" }, { status: 400 });
  }
}

export function GET(request: Request, context: RouteContext) { return proxy(request, context, "GET"); }
export function POST(request: Request, context: RouteContext) { return proxy(request, context, "POST"); }
export function PUT(request: Request, context: RouteContext) { return proxy(request, context, "PUT"); }
export function DELETE(request: Request, context: RouteContext) { return proxy(request, context, "DELETE"); }
