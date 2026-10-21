
import { NextRequest, NextResponse } from "next/server";
import { callBackend } from "@/lib/backend";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { role, message, conversation_id } = body;

    if (
      !["alya", "bima"].includes(role) ||
      typeof message !== "string" ||
      !message.trim()
    ) {
      return NextResponse.json(
        { error: "Role atau pesan tidak valid." },
        { status: 400 }
      );
    }

    const payload = {
      message: message.trim(),
      ...(typeof conversation_id === "string"
        ? { conversation_id }
        : {}),
    };

    const response = await callBackend(
      role,
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
  } catch {
    return NextResponse.json(
      { error: "Gagal memproses permintaan chat." },
      { status: 500 }
    );
  }
}
