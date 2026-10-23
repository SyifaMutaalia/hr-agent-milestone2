
import { NextResponse } from "next/server";
import { callAuthenticatedBackend } from "@/lib/backend";

export async function GET() {
  const response = await callAuthenticatedBackend(
    "/api/v1/auth/me"
  );

  if (!response.ok) {
    return NextResponse.json(
      { authenticated: false },
      { status: response.status }
    );
  }

  const user = await response.json();

  return NextResponse.json({
    authenticated: true,
    user,
  });
}
