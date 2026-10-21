import { NextRequest, NextResponse } from "next/server";
import { callBackend } from "@/lib/backend";
export async function GET(req: NextRequest) {
 const role = req.nextUrl.searchParams.get("role") || "";
 if (!["alya", "bima"].includes(role)) return NextResponse.json({ error: "Role karyawan diperlukan" }, { status: 400 });
 return callBackend(role, "/api/v1/leave-requests/me");
}
