import { NextResponse } from "next/server";
import { createRun } from "../../lib/store";
import { getCurrentUser } from "../../lib/auth";

export const dynamic = "force-dynamic";

// POST /api/rl-eval → enqueue a Phase 2 model-evaluation job.
// The user's model endpoint + API key are carried in the job to the worker,
// which calls the model HOST-SIDE (guarded by ssrf_guard). The key is never
// persisted to the run record — see lib/store.ts createRun.
export async function POST(request: Request) {
  const user = await getCurrentUser();
  if (!user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  let body: {
    taskId?: unknown;
    provider?: unknown;
    modelName?: unknown;
    modelEndpoint?: unknown;
    modelApiKey?: unknown;
    payload?: unknown;
  };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON body" }, { status: 400 });
  }

  const { taskId, provider, modelName, modelEndpoint, modelApiKey, payload } = body;
  const validProviders = ["openai", "gemini", "groq", "huggingface", "custom"];

  if (!taskId || typeof taskId !== "string") {
    return NextResponse.json({ error: "taskId is required" }, { status: 400 });
  }
  if (!provider || typeof provider !== "string" || !validProviders.includes(provider)) {
    return NextResponse.json({ error: "Invalid provider" }, { status: 400 });
  }
  if (!modelName || typeof modelName !== "string" || !modelName.trim()) {
    return NextResponse.json({ error: "modelName is required" }, { status: 400 });
  }

  const hasEndpoint = typeof modelEndpoint === "string" && modelEndpoint.trim() !== "";
  if (provider === "custom" && !hasEndpoint) {
    return NextResponse.json(
      { error: "Endpoint URL is required for custom provider" },
      { status: 400 },
    );
  }
  if (hasEndpoint && !/^https?:\/\//i.test(modelEndpoint as string)) {
    return NextResponse.json(
      { error: "modelEndpoint must be an http(s) URL" },
      { status: 400 },
    );
  }
  if (!modelApiKey || typeof modelApiKey !== "string") {
    return NextResponse.json(
      { error: "modelApiKey is required" },
      { status: 400 },
    );
  }

  const run = await createRun({
    type: "model_eval",
    taskId,
    provider,
    modelName,
    modelEndpoint: hasEndpoint ? (modelEndpoint as string).trim() : undefined,
    modelApiKey,
    payload: typeof payload === "string" ? payload : undefined,
  });

  return NextResponse.json({ runId: run.id, status: run.status }, { status: 201 });
}