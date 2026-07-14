import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const SCANNER_URL =
  process.env.SCANNER_MANAGER_URL ?? "http://scanner-manager:8001";

export async function GET() {
  const t0 = Date.now();
  try {
    const res = await fetch(`${SCANNER_URL}/health`, {
      signal: AbortSignal.timeout(5000),
      cache: "no-store",
    });
    const latency = Date.now() - t0;
    return NextResponse.json({ ok: res.ok, latency });
  } catch {
    return NextResponse.json({ ok: false, latency: Date.now() - t0 }, { status: 200 });
  }
}
