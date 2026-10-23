
import { NextRequest, NextResponse } from "next/server";
import { callAuthenticatedBackend } from "@/lib/backend";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    const { message, conversation_id } = body;

    if (
      typeof message !== "string" ||
      !message.trim()
    ) {
      return NextResponse.json(
        { error: "Pesan tidak valid." },
        { status: 400 }
      );
    }

    const payload = {
      message: message.trim(),
      ...(typeof conversation_id === "string"
        ? { conversation_id }
        : {}),
    };

    const response = await callAuthenticatedBackend(
      "/api/v1/chat",
      "POST",
      payload
    );

    if (!response.ok) {
      return response;
    }

    const data = await response.json();

    return NextResponse.json({
      ...data,
      mode: "api",
    });
  } catch (error) {
    console.error("[CHAT API ERROR]", error);

    return NextResponse.json(
      { error: "Gagal memproses permintaan chat." },
      { status: 500 }
    );
  }
}
