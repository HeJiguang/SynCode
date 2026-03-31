import { NextRequest, NextResponse } from "next/server";

const ACCESS_TOKEN_KEY = "syncode_access_token";

// 不需要登录就能访问的路径（相对于 basePath /app）
const PUBLIC_PATHS = ["/login", "/api/auth/send-code", "/api/auth/login"];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // 放行公开路径（静态资源、Next.js 内部路径自动被 matcher 过滤）
  if (PUBLIC_PATHS.some((p) => pathname.startsWith(p))) {
    return NextResponse.next();
  }

  const token = request.cookies.get(ACCESS_TOKEN_KEY)?.value;

  if (!token) {
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
