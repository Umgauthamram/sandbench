import { NextResponse } from "next/server";
import { getRun, listRuns } from "../../../lib/store";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const runId = url.searchParams.get("runId");

  try {
    if (runId) {
      const run = await getRun(runId);
      if (!run) {
        return NextResponse.json({ error: "Run not found" }, { status: 404 });
      }
      return NextResponse.json({ run });
    }
    const runs = await listRuns();
    return NextResponse.json({ runs });
  } catch {
    return NextResponse.json({ error: "Failed to query runs" }, { status: 500 });
  }
}
