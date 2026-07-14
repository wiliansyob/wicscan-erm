import { NextResponse } from "next/server";

export async function GET() {
  const zapUrl = process.env.ZAP_URL || "http://zap:8080";
  const t0 = performance.now();
  try {
    const res = await fetch(zapUrl, { signal: AbortSignal.timeout(3000), cache: "no-store" });
    const latency = Math.round(performance.now() - t0);
    return NextResponse.json({ ok: res.ok || res.status === 400 || res.status === 403, latency });
  } catch (e) {
    return NextResponse.json({ ok: false, latency: Math.round(performance.now() - t0) });
  }
}
