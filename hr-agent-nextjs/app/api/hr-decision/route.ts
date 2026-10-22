import { NextRequest, NextResponse } from "next/server";
import { callBackend } from "@/lib/backend";
import { getDemoSessionRole } from "@/lib/demo-session";

export async function PATCH(request: NextRequest) {
  try {
    const role = await getDemoSessionRole();

    if (role !== "hr") {
      return NextResponse.json(
        { detail: "Akses hanya untuk HR Admin." },
        { status: 403 }
      );
    }

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
    console.error("[HR_DECISION_ERROR]", error);

    return NextResponse.json(
      { detail: "Keputusan belum dapat diproses. Silakan coba kembali." },
      { status: 500 }
    );
  }
}