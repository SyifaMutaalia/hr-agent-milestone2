import { NextResponse } from "next/server";
import { callBackend } from "@/lib/backend";

export async function GET() {
  try {
    const response = await callBackend(
      "hr",
      "/api/v1/hr/leave-requests"
    );

    const data = await response.json();

    return NextResponse.json(data, {
      status: response.status,
    });
  } catch {
    return NextResponse.json(
      { error: "Gagal mengambil data pengajuan cuti HR." },
      { status: 502 }
    );
  }
}