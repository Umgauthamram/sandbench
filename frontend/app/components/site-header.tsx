import Link from "next/link";
import { Logo } from "./logo";

// Header for the public / marketing surface (landing, auth).
export function SiteHeader() {
  return (
    <header className="sticky top-0 z-20 border-b border-border/80 bg-background/80 backdrop-blur">
      <div className="mx-auto flex h-20 w-full items-center justify-between px-8 md:px-12 lg:px-16">
        <Logo />
        <nav className="flex items-center gap-5 text-[15px]">
          <Link
            href="/leaderboard"
            className="hidden rounded-md px-3.5 py-2 text-zinc-300 font-medium transition-colors hover:text-zinc-50 sm:block"
          >
            Leaderboard
          </Link>
          <Link
            href="/login"
            className="rounded-md px-3.5 py-2 text-zinc-300 font-medium transition-colors hover:text-zinc-50"
          >
            Log in
          </Link>
          <Link
            href="/signup"
            className="rounded-lg bg-grad-accent px-5 py-2.5 font-semibold text-zinc-950 transition-transform hover:scale-[1.02] shadow-sm shadow-orange-500/20"
          >
            Sign up
          </Link>
        </nav>
      </div>
    </header>
  );
}
