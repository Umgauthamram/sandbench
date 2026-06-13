import { NextResponse } from "next/server";
import { createRun, type SubmitInput } from "../../lib/store";
import type { SubmissionType } from "../../lib/types";
import { getCurrentUser } from "../../lib/auth";

export const dynamic = "force-dynamic";

const VALID_TYPES: SubmissionType[] = ["code", "files" /*, "api", "model"*/];
const MAX_PAYLOAD = 3 * 1024 * 1024; // 3 MB

export async function POST(request: Request) {
  const user = await getCurrentUser();
  if (!user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

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

  if (body.type === "files") {
    if (!body.archiveB64) {
      return NextResponse.json({ error: "archiveB64 is required for files type" }, { status: 400 });
    }
    if (!body.archiveKind || !["zip", "targz", "rawfile"].includes(body.archiveKind)) {
      return NextResponse.json({ error: "archiveKind must be 'zip', 'targz', or 'rawfile'" }, { status: 400 });
    }
    // Hard cap: reject if base64 string is larger than 7 MB
    if (body.archiveB64.length > 7 * 1024 * 1024) {
      return NextResponse.json({ error: "Archive payload size exceeds 7 MB limit" }, { status: 413 });
    }
  } else {
    if (body.payload && body.payload.length > MAX_PAYLOAD) {
      return NextResponse.json(
        { error: "payload exceeds size limit" },
        { status: 413 },
      );
    }
  }

  const run = await createRun({
    type: body.type,
    taskId: body.taskId,
    payload: body.type === "files" ? undefined : body.payload,
    archiveB64: body.type === "files" ? body.archiveB64 : undefined,
    archiveKind: body.type === "files" ? body.archiveKind : undefined,
  });

  return NextResponse.json({ runId: run.id, status: run.status }, { status: 201 });
}
