import Link from "next/link";
import { Logo } from "./logo";

// Header for the public / marketing surface (landing, auth).
export function SiteHeader() {
  return (
    <header className="sticky top-0 z-20 border-b border-border/80 bg-background/80 backdrop-blur">
      <div className="mx-auto flex h-16 w-full max-w-6xl items-center justify-between px-6">
        <Logo />
        <nav className="flex items-center gap-2 text-sm">
          <Link
            href="/leaderboard"
            className="hidden rounded-md px-3 py-2 text-zinc-300 transition-colors hover:text-zinc-50 sm:block"
          >
            Leaderboard
          </Link>
          <Link
            href="/login"
            className="rounded-md px-3 py-2 text-zinc-300 transition-colors hover:text-zinc-50"
          >
            Log in
          </Link>
          <Link
            href="/signup"
            className="rounded-md bg-zinc-50 px-3.5 py-2 font-medium text-zinc-950 transition-colors hover:bg-zinc-200"
          >
            Sign up
          </Link>
        </nav>
      </div>
    </header>
  );
}
