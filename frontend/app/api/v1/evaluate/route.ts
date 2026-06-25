import { NextResponse } from "next/server";
import { createRun } from "../../../lib/store";

export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  const authHeader = request.headers.get("Authorization");
  if (!authHeader || !authHeader.startsWith("Bearer sb_")) {
    return NextResponse.json({ error: "Unauthorized. Missing or invalid API token." }, { status: 401 });
  }

  let body: Record<string, unknown> = {};
  try {
    body = await request.json() as Record<string, unknown>;
  } catch {
    return NextResponse.json({ error: "Invalid JSON body" }, { status: 400 });
  }

  const { taskId, type, payload, archiveB64, archiveKind } = body;
  if (!taskId || typeof taskId !== "string") {
    return NextResponse.json({ error: "taskId is required" }, { status: 400 });
  }
  if (!type || typeof type !== "string" || !["code", "files"].includes(type)) {
    return NextResponse.json({ error: "type must be 'code' or 'files'" }, { status: 400 });
  }

  try {
    const run = await createRun({
      type: type as "code" | "files",
      taskId,
      payload: typeof payload === "string" ? payload : undefined,
      archiveB64: typeof archiveB64 === "string" ? archiveB64 : undefined,
      archiveKind: typeof archiveKind === "string" ? archiveKind : undefined,
    });
    return NextResponse.json({ runId: run.id, status: run.status }, { status: 201 });
  } catch {
    return NextResponse.json({ error: "Failed to submit evaluation run" }, { status: 500 });
  }
}
