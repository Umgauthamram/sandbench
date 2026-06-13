import { redirect } from "next/navigation";
import { PageHeader } from "../../components/ui";
import { getCurrentUser } from "../../lib/auth";
import { RlEvalForm } from "./rl-eval-form";

export const dynamic = "force-dynamic";

export default async function RlEvalPage() {
  const user = await getCurrentUser();
  if (!user) {
    redirect("/login");
  }

  return (
    <>
      <PageHeader
        title="Model evaluation"
        subtitle="Bring your own OpenAI-compatible model. We run it as the repair agent against a benchmark task and score the improvement (reward). Your model is called host-side only — the sandbox stays offline and just scores the produced code."
      />
      <RlEvalForm />
    </>
  );
}