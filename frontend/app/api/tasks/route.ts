import { NextResponse } from "next/server";
import { listTasks } from "../../lib/store";

export const dynamic = "force-dynamic";

// GET /api/tasks → available benchmark tasks.
export async function GET() {
  const tasks = await listTasks();
  return NextResponse.json({ tasks });
}
