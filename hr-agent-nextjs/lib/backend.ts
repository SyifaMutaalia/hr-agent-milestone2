import { NextResponse } from "next/server";

export type DemoRole = "alya" | "bima" | "hr" | "monitor";
export function bearerFor(role: string): string | undefined {
  const env: Record<string, string | undefined> = {
    alya: process.env.DEMO_TOKEN_ALYA,
    bima: process.env.DEMO_TOKEN_BIMA,
    hr: process.env.DEMO_TOKEN_HR,
    monitor: process.env.DEMO_TOKEN_MONITOR,
  };
  return env[role];
}
export async function callBackend(role: string, path: string, method = "GET", payload?: unknown) {
  const base = process.env.FASTAPI_URL;
  const token = bearerFor(role);
  if (!base || !token) return NextResponse.json({ error: "Backend/token belum dikonfigurasi; fitur ini membutuhkan FastAPI." }, { status: 503 });
  try {
    const res = await fetch(`${base.replace(/\/$/, "")}${path}`, {
      method, cache: "no-store", signal: AbortSignal.timeout(45000),
      headers: { Authorization: `Bearer ${token}`, ...(payload !== undefined ? { "Content-Type": "application/json" } : {}) },
      ...(payload !== undefined ? { body: JSON.stringify(payload) } : {}),
    });
    const result = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
    return NextResponse.json(result, { status: res.status });
  } catch { return NextResponse.json({ error: "Backend FastAPI tidak dapat dihubungi." }, { status: 502 }); }
}
