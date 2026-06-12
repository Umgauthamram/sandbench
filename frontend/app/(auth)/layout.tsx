import Link from "next/link";
import { Logo } from "../components/logo";

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="grid-backdrop flex flex-1 flex-col items-center justify-center px-6 py-16">
      <div className="mb-8">
        <Logo />
      </div>
      <div className="w-full max-w-sm rounded-2xl border border-border bg-panel p-8 shadow-2xl shadow-black/40">
        {children}
      </div>
      <p className="mt-6 text-xs text-zinc-600">
        <Link href="/" className="hover:text-zinc-400">
          ← Back to home
        </Link>
      </p>
    </div>
  );
}
