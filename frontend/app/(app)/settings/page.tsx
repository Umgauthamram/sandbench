import { redirect } from "next/navigation";
import { PageHeader } from "../../components/ui";
import { getCurrentUser } from "../../lib/auth";
import { SettingsForm } from "./settings-form";

export const dynamic = "force-dynamic";

export default async function SettingsPage() {
  const user = await getCurrentUser();
  if (!user) {
    redirect("/login");
  }

  return (
    <>
      <PageHeader
        title="Settings"
        subtitle="Manage your account settings and integration keys."
      />
      <SettingsForm user={user} />
    </>
  );
}
