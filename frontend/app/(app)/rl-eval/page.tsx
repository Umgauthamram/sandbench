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
      <RlEvalForm />
    </>
  );
}