import { NextRequest, NextResponse } from "next/server";
import { callBackend } from "@/lib/backend";
export async function POST(req: NextRequest) {
 const { role, proposal_id, idempotency_key } = await req.json();
 if (!["alya","bima"].includes(role) || typeof proposal_id !== "string" || !/^[a-zA-Z0-9_-]{1,128}$/.test(proposal_id) || typeof idempotency_key !== "string") return NextResponse.json({ error: "Invalid request" }, { status: 400 });
 return callBackend(role, `/api/v1/action-proposals/${encodeURIComponent(proposal_id)}/confirm`, "POST", { idempotency_key });
}
