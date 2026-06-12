import { NextResponse } from "next/server";
import { listRuns } from "../../lib/store";

// GET /api/runs → recent runs, newest first.
export async function GET() {
  const runs = await listRuns();
  return NextResponse.json({ runs });
}
