"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Logo } from "./logo";

const NAV = [
  { href: "/dashboard", label: "Dashboard", icon: "▦" },
  { href: "/submit", label: "New submission", icon: "↑" },
  { href: "/runs", label: "Runs", icon: "≡" },
  { href: "/leaderboard", label: "Leaderboard", icon: "★" },
  { href: "/tasks", label: "Benchmark tasks", icon: "◇" },
  { href: "/playground", label: "RL playground", icon: "∞" },
  { href: "/settings", label: "Settings", icon: "⚙" },
];

export function AppSidebar() {
  const pathname = usePathname();

  return (
    <aside className="hidden w-60 shrink-0 flex-col border-r border-border bg-panel md:flex">
      <div className="flex h-16 items-center border-b border-border px-5">
        <Logo href="/dashboard" />
      </div>
      <nav className="flex flex-1 flex-col gap-1 p-3">
        {NAV.map((item) => {
          const active =
            pathname === item.href || pathname.startsWith(item.href + "/");
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors ${
                active
                  ? "bg-zinc-800 text-zinc-50"
                  : "text-zinc-400 hover:bg-zinc-800/50 hover:text-zinc-200"
              }`}
            >
              <span className="w-4 text-center text-zinc-500">{item.icon}</span>
              {item.label}
            </Link>
          );
        })}
      </nav>
      <div className="border-t border-border p-3">
        <Link
          href="/login"
          className="flex items-center gap-3 rounded-md px-3 py-2 text-sm text-zinc-400 transition-colors hover:bg-zinc-800/50 hover:text-zinc-200"
        >
          <span className="w-4 text-center text-zinc-500">⎋</span>
          Log out
        </Link>
      </div>
    </aside>
  );
}
