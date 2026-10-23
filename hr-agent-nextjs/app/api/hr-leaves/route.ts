
import { callAuthenticatedBackend } from "@/lib/backend";

export async function GET() {
  try {
    return await callAuthenticatedBackend(
      "/api/v1/hr/leave-requests",
      "GET"
    );
  } catch (error) {
    console.error("[HR_LEAVES_ERROR]", error);

    return Response.json(
      { detail: "Data pengajuan belum dapat dimuat." },
      { status: 500 }
    );
  }
}
