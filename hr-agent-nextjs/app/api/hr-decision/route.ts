
import { NextRequest, NextResponse } from "next/server";
import { callAuthenticatedBackend } from "@/lib/backend";

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
        { detail: "Data keputusan tidak valid." },
        { status: 400 }
      );
    }

    return await callAuthenticatedBackend(
      `/api/v1/hr/leave-requests/${encodeURIComponent(
        request_id
      )}/decision`,
      "PATCH",
      { decision }
    );
  } catch (error) {
    console.error("[HR_DECISION_ERROR]", error);

    return NextResponse.json(
      {
        detail: "Keputusan belum dapat diproses.",
      },
      { status: 500 }
    );
  }
}
