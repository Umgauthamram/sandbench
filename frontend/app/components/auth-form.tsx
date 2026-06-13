"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

type Mode = "login" | "signup";

export function AuthForm({ mode }: { mode: Mode }) {
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const isSignup = mode === "signup";

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);

    const formData = new FormData(e.currentTarget);
    const email = formData.get("email") as string;
    const password = formData.get("password") as string;
    const name = isSignup ? (formData.get("name") as string) : "";

    try {
      const endpoint = isSignup ? "/api/auth/signup" : "/api/auth/login";
      const payload = isSignup ? { email, name, password } : { email, password };

      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.error || "Something went wrong. Please try again.");
      }

      router.push("/dashboard");
      router.refresh();
    } catch (err: any) {
      setError(err.message);
      setSubmitting(false);
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold tracking-tight text-zinc-50">
        {isSignup ? "Create your account" : "Welcome back"}
      </h1>
      <p className="mt-2 text-sm text-zinc-400 leading-relaxed">
        {isSignup
          ? "Start benchmarking submissions in isolation."
          : "Log in to submit and track your runs."}
      </p>

      <form onSubmit={onSubmit} className="mt-8 space-y-5">
        {isSignup && (
          <Field
            label="Name"
            name="name"
            type="text"
            placeholder="Ada Lovelace"
            autoComplete="name"
            required
          />
        )}
        <Field
          label="Email"
          name="email"
          type="email"
          placeholder="you@example.com"
          autoComplete="email"
          required
        />
        <Field
          label="Password"
          name="password"
          type="password"
          placeholder="••••••••"
          autoComplete={isSignup ? "new-password" : "current-password"}
          required
        />

        {error && (
          <div className="rounded-xl border border-red-500/20 bg-red-500/5 p-4 text-sm text-red-400 select-none leading-relaxed">
            <p className="font-semibold">Error</p>
            <p className="mt-0.5">{error}</p>
          </div>
        )}

        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded-xl bg-grad-accent px-4 py-3 text-[15px] font-bold text-white transition-all hover:scale-[1.01] active:scale-[0.99] disabled:opacity-60 shadow-md shadow-orange-500/10 cursor-pointer mt-2"
        >
          {submitting
            ? "Please wait…"
            : isSignup
              ? "Create account"
              : "Log in"}
        </button>
      </form>

      <div className="mt-6 text-center text-sm text-zinc-400">
        {isSignup ? (
          <>
            Already have an account?{" "}
            <Link href="/login" className="font-semibold text-accent hover:underline">
              Log in
            </Link>
          </>
        ) : (
          <>
            New here?{" "}
            <Link href="/signup" className="font-semibold text-accent hover:underline">
              Create an account
            </Link>
          </>
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
      <span className="mb-2 block text-xs font-semibold uppercase tracking-wider text-zinc-400">
        {label}
      </span>
      <input
        {...props}
        className="w-full rounded-xl border border-zinc-800 bg-zinc-950/80 px-4 py-3 text-[15px] text-zinc-100 placeholder:text-zinc-700 focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent transition-all"
      />
    </label>
  );
}
