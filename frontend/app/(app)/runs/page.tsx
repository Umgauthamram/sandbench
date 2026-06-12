import type { Metadata } from "next";
import { RunList } from "../../components/run-list";
import { PageHeader } from "../../components/ui";
import { listRuns } from "../../lib/store";

export const metadata: Metadata = { title: "Runs — SandBench" };
export const dynamic = "force-dynamic";

export default async function RunsPage() {
  const runs = await listRuns();
  return (
    <>
      <PageHeader
        title="Runs"
        subtitle="Every submission you've executed, newest first."
      />
      <RunList runs={runs} />
    </>
  );
}
