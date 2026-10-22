import { NextRequest, NextResponse } from "next/server";
import { timingSafeEqual } from "node:crypto";

export const runtime = "nodejs";

function sameSecret(a: string, b: string): boolean {
  const x = Buffer.from(a);
  const y = Buffer.from(b);
  return x.length === y.length && timingSafeEqual(x, y);
}

export async function POST(request: NextRequest) {
  const enabled = process.env.ENABLE_DEMO_RESET === "true";
  const environment = (process.env.APP_ENVIRONMENT ?? process.env.NODE_ENV ?? "").toLowerCase();
  if (!enabled || !["development", "demo", "test"].includes(environment)) {
    return NextResponse.json({ error: "Not found" }, { status: 404 });
  }

  const pin = process.env.DEMO_RESET_PIN;
  const secret = process.env.DEMO_RESET_SECRET;
  const base = process.env.FASTAPI_URL;
  if (!pin || !secret || !base) {
    return NextResponse.json({ error: "Reset belum dikonfigurasi." }, { status: 503 });
  }

  let submittedPin: unknown;
  try { submittedPin = (await request.json()).pin; }
  catch { return NextResponse.json({ error: "Permintaan tidak valid." }, { status: 400 }); }
  if (typeof submittedPin !== "string" || !sameSecret(submittedPin, pin)) {
    return NextResponse.json({ error: "PIN admin salah." }, { status: 403 });
  }

  try {
    const res = await fetch(`${base.replace(/\/$/, "")}/api/v1/hr/demo/reset`, {
      method: "POST", cache: "no-store",
      headers: { "X-Demo-Reset-Secret": secret },
      signal: AbortSignal.timeout(20000),
    });
    const data = await res.json().catch(() => ({ error: "Backend gagal merespons." }));
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json({ error: "FastAPI tidak dapat dihubungi." }, { status: 502 });
  }
}
