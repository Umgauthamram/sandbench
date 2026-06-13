"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Card } from "../../components/ui";
import { AlertTriangle, Key } from "lucide-react";
import type { SafeUser } from "../../lib/types";

export function SettingsForm({ user }: { user: SafeUser }) {
  const router = useRouter();
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [confirmEmail, setConfirmEmail] = useState("");
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [theme, setTheme] = useState("dark");

  const themes = [
    {
      id: "system",
      name: "System Theme",
      desc: "Synchronize theme with operating system settings",
      activeLabel: "System Default",
    },
    {
      id: "dark",
      name: "Lifted Dark",
      desc: "Deep zinc tones optimized for long debugging runs",
      activeLabel: "Active Theme",
    },
    {
      id: "light",
      name: "Light Mode",
      desc: "Clean high-contrast theme (Currently unavailable)",
      disabled: true,
      activeLabel: "Coming Soon",
    },
  ];

  const handleDeleteAccount = async (e: React.FormEvent) => {
    e.preventDefault();
    if (confirmEmail !== user.email) {
      setDeleteError("Email address does not match.");
      return;
    }

    setDeleting(true);
    setDeleteError(null);

    try {
      const res = await fetch("/api/auth/delete", {
        method: "POST",
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.error || "Failed to delete account");
      }

      router.push("/signup");
      router.refresh();
    } catch (err: any) {
      setDeleteError(err.message);
      setDeleting(false);
    }
  };

  return (
    <div className="max-w-4xl space-y-6">
      {/* Account Settings */}
      <Card>
        <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-400">
          Account Settings
        </h2>
        <div className="mt-4 space-y-4">
          <Field
            label="Display name"
            defaultValue={user.name}
            disabled
          />
          <p className="text-[11px] text-zinc-500 italic mt-0.5">
            Display name editing coming soon
          </p>
          <Field
            label="Email address"
            type="email"
            defaultValue={user.email}
            disabled
          />
        </div>
      </Card>
      <div className="flex items-center gap-3 pt-2">
        <button
          type="button"
          disabled
          className="rounded-lg bg-grad-accent px-5 py-2.5 text-sm font-semibold text-zinc-950 opacity-40 cursor-not-allowed select-none"
        >
          Save changes
        </button>
        <span className="text-xs text-zinc-500">
          (Display name changes are currently locked)
        </span>
      </div>


      {/* Integration Keys */}
      {/* <Card>
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-400">
            Integration Keys
          </h2>
          <span className="text-[10px] font-semibold text-orange-400/80 bg-orange-500/10 px-2 py-0.5 rounded border border-orange-500/20 uppercase tracking-wider select-none">
            coming soon
          </span>
        </div>
        <p className="mt-1 text-xs text-zinc-500">
          Used for benchmarking your submitted models. Stored encrypted and processed entirely in isolation.
        </p>
        <div className="mt-4 space-y-4">
          <div className="relative">
            <Field
              label="Model API key placeholder"
              type="password"
              placeholder="••••••••••••••••••••••••••••"
              disabled
            />
            <div className="absolute top-1/2 right-3 translate-y-[2px] text-zinc-600">
              <Key className="h-4 w-4" />
            </div>
          </div>
        </div>
      </Card> */}

      {/* Danger Zone */}
      <div className="rounded-xl border border-red-500/20 bg-red-500/5 p-6 space-y-4">
        <div className="flex items-center gap-2">
          <AlertTriangle className="h-5 w-5 text-red-500" />
          <h2 className="text-sm font-semibold uppercase tracking-wide text-red-400">
            Danger Zone
          </h2>
        </div>
        <p className="text-xs text-zinc-500 leading-relaxed">
          Once deleted, all account data, submissions, and trace histories will be permanently wiped.
        </p>
        
        {!showDeleteConfirm ? (
          <button
            type="button"
            onClick={() => setShowDeleteConfirm(true)}
            className="rounded-lg bg-red-950/40 border border-red-500/30 px-4 py-2 text-sm font-semibold text-red-400 hover:bg-red-500/10 transition-colors cursor-pointer"
          >
            Delete account
          </button>
        ) : (
          <form onSubmit={handleDeleteAccount} className="space-y-4 mt-2">
            <div className="space-y-2">
              <label className="block text-xs text-zinc-400">
                To confirm, type your email address <strong className="text-zinc-200 select-all">{user.email}</strong> below:
              </label>
              <input
                type="text"
                value={confirmEmail}
                onChange={(e) => setConfirmEmail(e.target.value)}
                placeholder={user.email}
                required
                className="w-full max-w-md rounded-lg border border-red-500/30 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-700 focus:border-red-500 focus:outline-none focus:ring-1 focus:ring-red-500"
              />
            </div>
            
            {deleteError && (
              <p className="text-xs text-red-400">{deleteError}</p>
            )}

            <div className="flex items-center gap-3">
              <button
                type="submit"
                disabled={deleting || confirmEmail !== user.email}
                className="rounded-lg bg-red-600 hover:bg-red-700 disabled:opacity-40 disabled:hover:bg-red-600 text-white px-4 py-2 text-sm font-semibold transition-colors cursor-pointer"
              >
                {deleting ? "Deleting..." : "Permanently Delete"}
              </button>
              <button
                type="button"
                disabled={deleting}
                onClick={() => {
                  setShowDeleteConfirm(false);
                  setConfirmEmail("");
                  setDeleteError(null);
                }}
                className="rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-300 px-4 py-2 text-sm font-semibold transition-colors cursor-pointer"
              >
                Cancel
              </button>
            </div>
          </form>
        )}
      </div>

    </div>
  );
}

function Field({
  label,
  ...props
}: { label: string } & React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-sm font-medium text-zinc-300">
        {label}
      </span>
      <input
        {...props}
        className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-600 focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent disabled:opacity-60 disabled:cursor-not-allowed"
      />
    </label>
  );
}
