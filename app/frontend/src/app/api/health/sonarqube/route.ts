import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const SONARQUBE_URL = process.env.SONARQUBE_URL ?? "http://sonarqube:9000";

export async function GET() {
  const t0 = Date.now();
  try {
    const res = await fetch(`${SONARQUBE_URL}/api/system/status`, {
      signal: AbortSignal.timeout(5000),
      cache: "no-store",
    });
    const latency = Date.now() - t0;
    // SonarQube returns JSON with "status": "UP"
    if (res.ok) {
      const data = await res.json();
      return NextResponse.json({ ok: data.status === "UP", latency });
    }
    return NextResponse.json({ ok: false, latency });
  } catch {
    return NextResponse.json({ ok: false, latency: Date.now() - t0 }, { status: 200 });
  }
}
