"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Logo } from "./logo";
import { 
  LayoutDashboard, 
  Plus, 
  ListChecks, 
  Trophy, 
  Boxes, 
  Bot, 
  Settings, 
  LogOut 
} from "lucide-react";
import { useRouter } from "next/navigation";
import type { SafeUser } from "../lib/types";

const NAV = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/submit", label: "New submission", icon: Plus },
  { href: "/runs", label: "Runs", icon: ListChecks },
  { href: "/leaderboard", label: "Leaderboard", icon: Trophy },
  { href: "/tasks", label: "Benchmark tasks", icon: Boxes },
  { href: "/playground", label: "RL playground", icon: Bot },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function AppSidebar({ user }: { user?: SafeUser | null }) {
  const pathname = usePathname();
  const router = useRouter();

  const handleLogout = async () => {
    try {
      const res = await fetch("/api/auth/logout", { method: "POST" });
      if (res.ok) {
        router.push("/login");
        router.refresh();
      }
    } catch (err) {
      console.error("Logout error:", err);
    }
  };

  return (
    <aside className="hidden w-60 shrink-0 flex-col border-r border-border bg-zinc-900 md:flex select-none">
      {/* Gradient accent top bar */}
      <div className="h-0.5 w-full bg-grad-accent flex-shrink-0" />
      <div className="flex h-16 items-center border-b border-border px-5">
        <Logo href="/dashboard" gradient />
      </div>
      <nav className="flex flex-1 flex-col gap-0.5 p-3">
        {NAV.map((item) => {
          const Icon = item.icon;
          const active =
            pathname === item.href || pathname.startsWith(item.href + "/");
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-150 ${
                active
                  ? "bg-blue-500/10 text-zinc-50 shadow-sm ring-1 ring-blue-500/20"
                  : "text-zinc-400 hover:bg-zinc-800/60 hover:text-zinc-200"
              }`}
            >
              <Icon
                className={`h-4 w-4 shrink-0 ${
                  active ? "text-blue-400" : "text-zinc-500"
                }`}
              />
              {item.label}
              {active && (
                <span className="ml-auto h-1.5 w-1.5 rounded-full bg-blue-400" />
              )}
            </Link>
          );
        })}
      </nav>
      <div className="border-t border-border p-3 flex flex-col">
        {user && (
          <div className="flex flex-col px-3 py-2 mb-2 bg-zinc-950/40 rounded-lg border border-border/40 select-text">
            <span className="text-sm font-semibold text-zinc-300 truncate">{user.name}</span>
            <span className="text-xs text-zinc-500 truncate mt-0.5">{user.email}</span>
          </div>
        )}
        <button
          onClick={handleLogout}
          className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-zinc-500 transition-all hover:bg-zinc-800/60 hover:text-zinc-300 cursor-pointer text-left"
        >
          <LogOut className="h-4 w-4 shrink-0" />
          Log out
        </button>
      </div>
    </aside>
  );
}

