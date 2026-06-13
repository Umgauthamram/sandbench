import { NextResponse } from "next/server";
import { createRun, type SubmitInput } from "../../lib/store";
import type { SubmissionType } from "../../lib/types";

const VALID_TYPES: SubmissionType[] = ["code", "files", "api", "model"];
const MAX_PAYLOAD = 256 * 1024;

export async function POST(request: Request) {
  let body: Partial<SubmitInput>;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON body" }, { status: 400 });
  }

  if (!body.type || !VALID_TYPES.includes(body.type)) {
    return NextResponse.json(
      { error: `type must be one of ${VALID_TYPES.join(", ")}` },
      { status: 400 },
    );
  }
  if (!body.taskId) {
    return NextResponse.json({ error: "taskId is required" }, { status: 400 });
  }
  if (body.payload && body.payload.length > MAX_PAYLOAD) {
    return NextResponse.json(
      { error: "payload exceeds 256 KB limit" },
      { status: 413 },
    );
  }

  const run = await createRun({
    type: body.type,
    taskId: body.taskId,
    payload: body.payload,
  });

  return NextResponse.json({ runId: run.id, status: run.status }, { status: 201 });
}
