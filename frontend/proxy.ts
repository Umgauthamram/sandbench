import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const token = request.cookies.get("sb_session")?.value;

  const protectedPaths = [
    "/dashboard",
    "/submit",
    "/runs",
    "/leaderboard",
    "/tasks",
    "/playground",
    "/settings",
  ];

  const isProtected = protectedPaths.some(
    (path) => pathname === path || pathname.startsWith(`${path}/`)
  );

  const authPaths = ["/login", "/signup"];
  const isAuthPath = authPaths.some(
    (path) => pathname === path || pathname.startsWith(`${path}/`)
  );

  // Redirect to login if accessing a protected page without a session
  if (isProtected && !token) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  // Redirect to dashboard if logged-in user hits /login or /signup
  if (isAuthPath && token) {
    return NextResponse.redirect(new URL("/dashboard", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for:
     * - api (handled internally by route handlers for JSON responses)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - public files/assets
     */
    "/((?!api|_next/static|_next/image|favicon.ico).*)",
  ],
};
