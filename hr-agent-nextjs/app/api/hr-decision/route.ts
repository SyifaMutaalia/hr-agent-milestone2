import { NextRequest, NextResponse } from "next/server";
import { callBackend } from "@/lib/backend";

export async function PATCH(request: NextRequest) {
  try {
    const body = await request.json();
    const { request_id, decision } = body;

    if (
      typeof request_id !== "string" ||
      !request_id.trim() ||
      !["approved", "rejected"].includes(decision)
    ) {
      return NextResponse.json(
        { detail: "Data keputusan tidak valid" },
        { status: 400 }
      );
    }

    const response = await callBackend(
      "hr",
      `/api/v1/hr/leave-requests/${encodeURIComponent(request_id)}/decision`,
      "PATCH",
      { decision }
    );

    const result = await response.json();

    return NextResponse.json(result, {
      status: response.status,
    });
  } catch (error) {
    console.error("HR decision error:", error);

    return NextResponse.json(
      { detail: "Gagal memproses keputusan HR" },
      { status: 500 }
    );
  }
}