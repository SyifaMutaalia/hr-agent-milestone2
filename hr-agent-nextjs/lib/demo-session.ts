import "server-only";
import { createHmac, timingSafeEqual } from "node:crypto";
import { cookies } from "next/headers";

export type DemoRole = "alya" | "bima" | "hr" | "monitor";

const COOKIE_NAME = "hr_agent_demo_session";

export function isDemoRole(value: unknown): value is DemoRole {
  return (
    value === "alya" ||
    value === "bima" ||
    value === "hr" ||
    value === "monitor"
  );
}

function getSecret(): string {
  const secret = process.env.DEMO_SESSION_SECRET;

  if (!secret || secret.length < 32) {
    throw new Error("DEMO_SESSION_SECRET belum dikonfigurasi");
  }

  return secret;
}

function sign(payload: string): string {
  return createHmac("sha256", getSecret())
    .update(payload)
    .digest("hex");
}

export function createDemoSession(role: DemoRole): string {
  const payload = Buffer.from(
    JSON.stringify({
      role,
      expiresAt: Date.now() + 8 * 60 * 60 * 1000,
    })
  ).toString("base64url");

  return `${payload}.${sign(payload)}`;
}

export async function getDemoSessionRole(): Promise<DemoRole | null> {
  const cookieStore = await cookies();
  const value = cookieStore.get(COOKIE_NAME)?.value;

  if (!value) return null;

  const [payload, signature, extra] = value.split(".");

  if (!payload || !signature || extra) return null;

  const expected = Buffer.from(sign(payload), "hex");
  const actual = Buffer.from(signature, "hex");

  if (
    expected.length !== actual.length ||
    !timingSafeEqual(expected, actual)
  ) {
    return null;
  }

  try {
    const data = JSON.parse(
      Buffer.from(payload, "base64url").toString("utf8")
    );

    if (
      !isDemoRole(data.role) ||
      typeof data.expiresAt !== "number" ||
      Date.now() >= data.expiresAt
    ) {
      return null;
    }

    return data.role;
  } catch {
    return null;
  }
}

export const DEMO_COOKIE_NAME = COOKIE_NAME;