import { NextRequest, NextResponse } from "next/server";
import { callBackend } from "@/lib/backend";
export async function GET(req: NextRequest) {
 const role = req.nextUrl.searchParams.get("role");
 const resource = req.nextUrl.searchParams.get("resource");
 if (role !== "monitor" || !["summary", "alerts"].includes(resource || "")) return NextResponse.json({ error: "Not allowed" }, { status: 403 });
 return callBackend("monitor", `/api/v1/monitoring/${resource}`);
}
