import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { RunList } from "../../components/run-list";
import { PageHeader } from "../../components/ui";
import { listRuns } from "../../lib/store";
import { getCurrentUser } from "../../lib/auth";

export const metadata: Metadata = { title: "Runs — SandBench" };
export const dynamic = "force-dynamic";

export default async function RunsPage() {
  const user = await getCurrentUser();
  if (!user) {
    redirect("/login");
  }
  const runs = await listRuns(user.id);
  return (
    <>
     
      <RunList runs={runs} />
    </>
  );
}

