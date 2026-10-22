import { NextResponse } from "next/server";
import { DEMO_COOKIE_NAME } from "@/lib/demo-session";

export async function POST() {
  const response = NextResponse.json({
    status: "ok",
    message: "Sesi demo berhasil diakhiri",
  });

  response.cookies.set(DEMO_COOKIE_NAME, "", {
    httpOnly: true,
    secure: false,
    sameSite: "strict",
    path: "/",
    maxAge: 0,
  });

  return response;
}