import { getRun } from "../../../../lib/store";
import { getCurrentUser } from "../../../../lib/auth";
import type { SSEMessage, SSEError } from "../../../../lib/types";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET(
  request: Request,
  ctx: { params: Promise<{ id: string }> },
) {
  const user = await getCurrentUser();
  if (!user) {
    return new Response(JSON.stringify({ error: "Unauthorized" }), {
      status: 401,
      headers: { "Content-Type": "application/json" },
    });
  }

  const { id } = await ctx.params;
  const run = await getRun(id);
  if (!run) {
    return new Response(JSON.stringify({ error: "Run not found" }), {
      status: 404,
      headers: { "Content-Type": "application/json" },
    });
  }

  // Scoping check: users can only stream their own runs
  if (run.userId && run.userId !== user.id) {
    return new Response(JSON.stringify({ error: "Forbidden" }), {
      status: 403,
      headers: { "Content-Type": "application/json" },
    });
  }

  const encoder = new TextEncoder();
  let intervalId: NodeJS.Timeout | null = null;

  const stream = new ReadableStream({
    async start(controller) {
      let lastStatus = run.status;
      let lastVerdict = run.verdict ?? null;
      let lastScore = run.score ?? null;
      let lastLogsLength = run.logs.length;

      // Emit full current state as first event
      const initialPayload: SSEMessage = {
        status: lastStatus,
        verdict: lastVerdict,
        score: lastScore,
        logLines: run.logs,
      };
      controller.enqueue(encoder.encode(`data: ${JSON.stringify(initialPayload)}\n\n`));

      const isTerminal = (s: string) =>
        s === "done" || s === "quarantined" || s === "error";

      if (isTerminal(lastStatus)) {
        controller.enqueue(
          encoder.encode(`event: end\ndata: ${JSON.stringify({ status: lastStatus })}\n\n`)
        );
        controller.close();
        return;
      }

      // Poll every 1000ms server-side
      const startTime = Date.now();
      const SAFETY_TIMEOUT_MS = 120000; // 120 seconds

      intervalId = setInterval(async () => {
        try {
          const now = Date.now();
          if (now - startTime >= SAFETY_TIMEOUT_MS) {
            controller.enqueue(
              encoder.encode(`event: end\ndata: ${JSON.stringify({ status: lastStatus })}\n\n`)
            );
            if (intervalId) clearInterval(intervalId);
            controller.close();
            return;
          }

          const currentRun = await getRun(id);
          if (!currentRun) {
            controller.enqueue(
              encoder.encode(`event: error\ndata: ${JSON.stringify({ error: "not found" } as SSEError)}\n\n`)
            );
            if (intervalId) clearInterval(intervalId);
            controller.close();
            return;
          }

          const currentStatus = currentRun.status;
          const currentVerdict = currentRun.verdict ?? null;
          const currentScore = currentRun.score ?? null;
          const currentLogs = currentRun.logs || [];

          const statusChanged = currentStatus !== lastStatus;
          const verdictChanged = currentVerdict !== lastVerdict;
          const scoreChanged = currentScore !== lastScore;
          const logsAdded = currentLogs.length > lastLogsLength;

          if (statusChanged || verdictChanged || scoreChanged || logsAdded) {
            const newLines = currentLogs.slice(lastLogsLength);
            lastStatus = currentStatus;
            lastVerdict = currentVerdict;
            lastScore = currentScore;
            lastLogsLength = currentLogs.length;

            const payload: SSEMessage = {
              status: currentStatus,
              verdict: currentVerdict,
              score: currentScore,
              logLines: newLines,
            };
            controller.enqueue(encoder.encode(`data: ${JSON.stringify(payload)}\n\n`));
          }

          if (isTerminal(currentStatus)) {
            controller.enqueue(
              encoder.encode(`event: end\ndata: ${JSON.stringify({ status: currentStatus })}\n\n`)
            );
            if (intervalId) clearInterval(intervalId);
            controller.close();
          }
        } catch (err) {
          console.error("SSE polling error:", err);
          controller.enqueue(
            encoder.encode(
              `event: error\ndata: ${JSON.stringify({ error: "internal error" } as SSEError)}\n\n`
            )
          );
          if (intervalId) clearInterval(intervalId);
          controller.close();
        }
      }, 1000);
    },
    cancel() {
      if (intervalId) {
        clearInterval(intervalId);
      }
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      "Connection": "keep-alive",
    },
  });
}
