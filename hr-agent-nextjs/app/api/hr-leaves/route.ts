import { NextResponse } from "next/server";
import { callBackend } from "@/lib/backend";
import { getDemoSessionRole } from "@/lib/demo-session";

export async function GET() {
  try {
    const role = await getDemoSessionRole();

    if (role !== "hr") {
      return NextResponse.json(
        { detail: "Akses hanya untuk HR Admin." },
        { status: 403 }
      );
    }

    const response = await callBackend(
      "hr",
      "/api/v1/hr/leave-requests"
    );

    const data = await response.json();

    return NextResponse.json(data, {
      status: response.status,
    });
  } catch (error) {
    console.error("[HR_LEAVES_ERROR]", error);

    return NextResponse.json(
      { detail: "Data pengajuan belum dapat dimuat." },
      { status: 500 }
    );
  }
}