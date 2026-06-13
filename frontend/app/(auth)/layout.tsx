import Link from "next/link";
import { Logo } from "../components/logo";
import { ArrowLeft } from "lucide-react";

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="grid-backdrop flex flex-1 flex-col items-center justify-center px-6 py-16 bg-zinc-950 min-h-screen">
      <div className="mb-8">
        <Logo />
      </div>
      <div className="w-full max-w-md rounded-2xl border border-zinc-800 bg-panel p-10 shadow-2xl shadow-black/60">
        {children}
      </div>
      <p className="mt-8 text-sm text-zinc-500">
        <Link href="/" className="inline-flex items-center gap-1.5 hover:text-zinc-400 transition-colors">
          <ArrowLeft className="h-3 w-3" /> Back to home
        </Link>
      </p>
    </div>
  );
}
