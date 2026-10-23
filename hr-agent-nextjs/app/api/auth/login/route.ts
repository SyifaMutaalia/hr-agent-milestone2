
import { NextRequest, NextResponse } from "next/server";
import { SESSION_COOKIE_NAME } from "@/lib/backend";

export async function POST(request: NextRequest) {
  try {
    const { email, password } = await request.json();

    if (
      typeof email !== "string" ||
      !email.trim() ||
      typeof password !== "string" ||
      !password
    ) {
      return NextResponse.json(
        { error: "Email dan password wajib diisi." },
        { status: 400 }
      );
    }

    const base = process.env.FASTAPI_URL;

    if (!base) {
      return NextResponse.json(
        { error: "FASTAPI_URL belum dikonfigurasi." },
        { status: 503 }
      );
    }

    const backendResponse = await fetch(
      `${base.replace(/\/$/, "")}/api/v1/auth/login`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: email.trim(),
          password,
        }),
        cache: "no-store",
        signal: AbortSignal.timeout(15000),
      }
    );

    const data = await backendResponse.json().catch(() => ({}));

    if (!backendResponse.ok) {
      return NextResponse.json(
        {
          error:
            backendResponse.status === 401
              ? "Email atau password salah."
              : data.detail || "Login gagal.",
        },
        { status: backendResponse.status }
      );
    }

    if (
      typeof data.access_token !== "string" ||
      !["employee", "hr_admin", "monitoring_admin"].includes(data.role)
    ) {
      return NextResponse.json(
        { error: "Respons autentikasi tidak valid." },
        { status: 502 }
      );
    }

    const response = NextResponse.json({
      success: true,
      employee_id: data.employee_id,
      display_name: data.display_name,
      role: data.role,
    });

    response.cookies.set({
      name: SESSION_COOKIE_NAME,
      value: data.access_token,
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      path: "/",
      maxAge: 60 * 60 * 8,
    });

    return response;
  } catch (error) {
    console.error("[AUTH LOGIN ERROR]", {
      name: error instanceof Error ? error.name : "Unknown",
      message: error instanceof Error ? error.message : String(error),
    });

    const isTimeout =
      error instanceof Error &&
      (error.name === "TimeoutError" || error.name === "AbortError");

    return NextResponse.json(
      {
        error: isTimeout
          ? "Layanan login terlalu lama merespons."
          : "Tidak dapat terhubung ke layanan login.",
      },
      { status: isTimeout ? 504 : 502 }
    );
  }
}