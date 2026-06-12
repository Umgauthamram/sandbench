import { AppSidebar } from "../components/app-sidebar";
import { Logo } from "../components/logo";

export default function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-1">
      <AppSidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        {/* Mobile header (sidebar is hidden < md) */}
        <header className="flex h-16 items-center border-b border-border px-5 md:hidden">
          <Logo href="/dashboard" />
        </header>
        <main className="mx-auto w-full max-w-6xl flex-1 px-6 py-8">
          {children}
        </main>
      </div>
    </div>
  );
}
