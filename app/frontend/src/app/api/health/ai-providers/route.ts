import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const AI_GATEWAY_URL = process.env.AI_GATEWAY_URL ?? "http://ai-gateway:8002";

export async function GET() {
  try {
    const res = await fetch(`${AI_GATEWAY_URL}/api/v1/providers`, {
      signal: AbortSignal.timeout(5000),
      cache: "no-store",
    });
    if (!res.ok) {
      return NextResponse.json({ ok: false, providers: {} });
    }
    const data = await res.json();
    return NextResponse.json({ ok: true, providers: data.providers });
  } catch {
    return NextResponse.json({ ok: false, providers: {} }, { status: 200 });
  }
}
