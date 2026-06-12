"use client";

import { useState } from "react";
import { Card, PageHeader } from "../../components/ui";

export default function SettingsPage() {
  const [saved, setSaved] = useState(false);

  function onSave(e: React.FormEvent) {
    e.preventDefault();
    // TODO: PATCH /settings { displayName, anthropicKey } — keys stored encrypted.
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }

  return (
    <>
      <PageHeader title="Settings" subtitle="Account and integration keys." />

      <form onSubmit={onSave} className="max-w-xl space-y-6">
        <Card>
          <h2 className="text-sm font-medium uppercase tracking-wide text-zinc-500">
            Profile
          </h2>
          <div className="mt-4 space-y-4">
            <Field label="Display name" defaultValue="ada" />
            <Field
              label="Email"
              type="email"
              defaultValue="ada@example.com"
              disabled
            />
          </div>
        </Card>

        <Card>
          <h2 className="text-sm font-medium uppercase tracking-wide text-zinc-500">
            Integration keys
          </h2>
          <p className="mt-1 text-xs text-zinc-500">
            Used by the analysis engine (LLM review) and for model submissions.
            Stored encrypted; never logged.
          </p>
          <div className="mt-4 space-y-4">
            <Field
              label="Anthropic API key"
              type="password"
              placeholder="sk-ant-…"
            />
          </div>
        </Card>

        <div className="flex items-center gap-3">
          <button
            type="submit"
            className="rounded-lg bg-zinc-50 px-5 py-2.5 text-sm font-medium text-zinc-950 transition-colors hover:bg-zinc-200"
          >
            Save changes
          </button>
          {saved && <span className="text-sm text-clean">Saved ✓</span>}
        </div>
      </form>
    </>
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
        className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-600 focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent disabled:opacity-60"
      />
    </label>
  );
}
