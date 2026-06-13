import { NextResponse } from "next/server";
import { getRun } from "../../../lib/store";
import { getCurrentUser } from "../../../lib/auth";

export const dynamic = "force-dynamic";

// GET /api/runs/{id} → a single run's status + result.
export async function GET(
  _request: Request,
  ctx: { params: Promise<{ id: string }> },
) {
  const user = await getCurrentUser();
  if (!user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const { id } = await ctx.params;
  const run = await getRun(id);
  if (!run) {
    return NextResponse.json({ error: "Run not found" }, { status: 404 });
  }

  // Scoping check: users can only view their own runs
  if (run.userId && run.userId !== user.id) {
    return NextResponse.json({ error: "Forbidden" }, { status: 403 });
  }

  return NextResponse.json({ run });
}
