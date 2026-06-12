import { NextResponse } from "next/server";
import { getRun } from "../../../lib/store";

// GET /api/runs/{id} → a single run's status + result.
// TODO: when status is "running", upgrade this to an SSE stream
//       (Content-Type: text/event-stream) so the run view can live-tail logs.
export async function GET(
  _request: Request,
  ctx: { params: Promise<{ id: string }> },
) {
  const { id } = await ctx.params;
  const run = await getRun(id);
  if (!run) {
    return NextResponse.json({ error: "Run not found" }, { status: 404 });
  }
  return NextResponse.json({ run });
}
