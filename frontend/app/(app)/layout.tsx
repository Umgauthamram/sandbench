import { redirect } from "next/navigation";
import { AppSidebar } from "../components/app-sidebar";
import { Logo } from "../components/logo";
import { getCurrentUser } from "../lib/auth";

export default async function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const user = await getCurrentUser();
  if (!user) {
    redirect("/login");
  }

  return (
    <div className="flex flex-1 min-h-screen bg-[#09090b]">
      <AppSidebar user={user} />
      <div className="flex min-w-0 flex-1 flex-col">
        {/* Mobile header (sidebar is hidden < md) */}
        <header className="flex h-16 items-center border-b border-border px-5 md:hidden bg-zinc-900/80 backdrop-blur-sm">
          <Logo href="/dashboard" />
        </header>
        <main className="w-full flex-1 px-8 py-10 md:px-12 lg:px-16">
          {children}
        </main>
      </div>
    </div>
  );
}

