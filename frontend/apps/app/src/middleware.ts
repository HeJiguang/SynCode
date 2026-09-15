import { NextRequest, NextResponse } from "next/server";
import { DEMO_SESSION_KEY } from "@aioj/api";
import { frontendDemoLoginEnabled, frontendPreviewMode } from "@aioj/config";

const ACCESS_TOKEN_KEY = "syncode_access_token";

// 不需要登录就能访问的路径（相对于 basePath /app）
const PUBLIC_PATHS = ["/login", "/api/auth/send-code", "/api/auth/login", "/api/auth/demo"];

export function middleware(request: NextRequest) {
  if (frontendPreviewMode) {
    return NextResponse.next();
  }

  const { pathname } = request.nextUrl;

  // 放行公开路径（静态资源、Next.js 内部路径自动被 matcher 过滤）
  if (PUBLIC_PATHS.some((p) => pathname.startsWith(p))) {
    return NextResponse.next();
  }

  const token = request.cookies.get(ACCESS_TOKEN_KEY)?.value;
  const demoSession =
    frontendDemoLoginEnabled &&
    process.env.SYNCODE_DEMO_LOGIN_ENABLED === "true" &&
    request.cookies.get(DEMO_SESSION_KEY)?.value === "1";

  if (!token && !demoSession) {
    const loginUrl = request.nextUrl.clone();
    loginUrl.pathname = "/login";
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  // 只匹配 app 下的页面路由，排除 _next 静态资源和 favicon
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
