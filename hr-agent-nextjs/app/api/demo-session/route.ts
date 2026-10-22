import { NextResponse } from "next/server";
import { getDemoSessionRole } from "@/lib/demo-session";

export async function GET() {
  try {
    const role = await getDemoSessionRole();

    return NextResponse.json(
      { authenticated: role !== null, role },
      {
        headers: {
          "Cache-Control": "no-store",
        },
      }
    );
  } catch (error) {
    console.error("[DEMO_SESSION_ERROR]", error);

    return NextResponse.json(
      { authenticated: false, role: null },
      { status: 500 }
    );
  }
}