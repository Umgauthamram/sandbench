import { NextResponse } from "next/server";
import { listTasks } from "../../../lib/store";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const tasks = await listTasks();
    const suites = Array.from(new Set(tasks.map((t) => t.suite || "core"))).sort();
    return NextResponse.json({ suites });
  } catch {
    return NextResponse.json({ error: "Failed to list suites" }, { status: 500 });
  }
}
