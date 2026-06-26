"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Card } from "./ui";
import type { SSEMessage } from "../lib/types";

interface RunStreamProps {
  id: string;
  initialLogs: string[];
  initialStatus: string;
}

export function RunStream({ id, initialLogs, initialStatus }: RunStreamProps) {
  const router = useRouter();
  const [logs, setLogs] = useState<string[]>(initialLogs);
  const [status, setStatus] = useState<string>(initialStatus);

  useEffect(() => {
    if (["done", "quarantined", "error"].includes(initialStatus)) return;

    const es = new EventSource(`/api/runs/${id}/stream`);
    let closed = false;
    let isFirst = true;
    const finish = (refresh: boolean) => {
      if (closed) return;
      closed = true;
      es.close();
      if (refresh) router.refresh();
    };

    es.onmessage = (event) => {
      try {
        const data: SSEMessage = JSON.parse(event.data);
        const wasFirst = isFirst;
        isFirst = false;

        if (data.logLines?.length) {
          if (wasFirst) {
            setLogs(data.logLines);
          } else {
            setLogs((prev) => [...prev, ...data.logLines]);
          }
        }
        if (data.status) {
          setStatus(data.status);
        }
      } catch (err) {
        console.error("Failed to parse SSE message", err);
      }
    };

    es.addEventListener("end", () => finish(true));
    es.addEventListener("error", () => finish(true));   // custom server "error" event
    es.onerror = () => finish(true);                    // transport-level error

    return () => {
      closed = true;
      es.close();
    };
  }, [id, initialStatus, router]);

  const isRunning = status === "running" || status === "queued";

  return (
    <Card className="lg:col-span-2">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-medium uppercase tracking-wide text-zinc-500">
          Run logs
        </h2>
        {isRunning && (
          <span className="flex items-center gap-1.5 text-xs text-accent">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-current" />
            streaming
          </span>
        )}
      </div>
      <pre className="max-h-80 overflow-auto rounded-lg bg-zinc-950 border border-zinc-800 p-4 font-mono text-xs leading-6 text-zinc-300">
        {logs.join("\n")}
        {isRunning && (
          <span className="inline-block ml-0.5 h-3 w-1.5 bg-blue-400 animate-pulse align-middle" />
        )}
      </pre>
    </Card>
  );
}
