import { NextResponse } from "next/server";
import { listLeaderboard } from "../../lib/store";

// GET /api/leaderboard → ranked entries.
export async function GET() {
  const entries = await listLeaderboard();
  return NextResponse.json({ entries });
}
