import { NextResponse } from "next/server";
import { listLeaderboard } from "../../lib/store";

// GET /api/leaderboard → ranked entries.
export async function GET(request: Request) {
  const url = new URL(request.url);
  const entries = await listLeaderboard({
    suite: url.searchParams.get("suite") || undefined,
    version: url.searchParams.get("version") || undefined,
  });
  return NextResponse.json({ entries });
}
