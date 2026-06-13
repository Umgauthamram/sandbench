"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export function RunPoller({ id, initialStatus }: { id: string; initialStatus: string }) {
  const router = useRouter();

  useEffect(() => {
    // Stop polling if the status is final
    if (initialStatus === "done" || initialStatus === "quarantined" || initialStatus === "error") {
      return;
    }

    const interval = setInterval(async () => {
      try {
        const res = await fetch(`/api/runs/${id}`);
        if (res.ok) {
          const data = await res.json();
          // If status changed or is still running, refresh the server component
          if (data.run?.status !== initialStatus) {
            router.refresh();
          }
        }
      } catch (err) {
        console.error("Failed to poll run status", err);
      }
    }, 1500);

    return () => clearInterval(interval);
  }, [id, initialStatus, router]);

  return null;
}
