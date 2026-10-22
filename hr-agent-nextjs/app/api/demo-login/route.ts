import { NextRequest, NextResponse } from "next/server";
import {
  createDemoSession,
  DEMO_COOKIE_NAME,
  isDemoRole,
} from "@/lib/demo-session";

export async function POST(request: NextRequest) {
  // Login tanpa password hanya diizinkan untuk demo lokal.
  const hostname = request.nextUrl.hostname;

if (
  process.env.NODE_ENV !== "development" ||
  !["127.0.0.1", "localhost"].includes(hostname)
) {
    return NextResponse.json(
      { detail: "Login demo tidak tersedia" },
      { status: 403 }
    );
  }

  try {
    const body = await request.json();

    if (!isDemoRole(body.role)) {
      return NextResponse.json(
        { detail: "Role tidak valid" },
        { status: 400 }
      );
    }

    const session = createDemoSession(body.role);

    const response = NextResponse.json({
      status: "ok",
      role: body.role,
    });

    response.cookies.set(DEMO_COOKIE_NAME, session, {
      httpOnly: true,
      secure: false, // Khusus development HTTP localhost
      sameSite: "strict",
      path: "/",
      maxAge: 8 * 60 * 60,
    });

    return response;
  } catch {
    return NextResponse.json(
      { detail: "Gagal membuat sesi demo" },
      { status: 500 }
    );
  }
}