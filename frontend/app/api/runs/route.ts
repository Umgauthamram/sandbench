import { NextResponse } from "next/server";
import { listRuns } from "../../lib/store";
import { getCurrentUser } from "../../lib/auth";

export const dynamic = "force-dynamic";

// GET /api/runs → recent runs for the current authenticated user.
export async function GET() {
  const user = await getCurrentUser();
  if (!user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  const runs = await listRuns(user.id);
  return NextResponse.json({ runs });
}
