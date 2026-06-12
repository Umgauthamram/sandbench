"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

type Mode = "login" | "signup";

export function AuthForm({ mode }: { mode: Mode }) {
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);
  const isSignup = mode === "signup";

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setSubmitting(true);
    // TODO: POST to the gateway's /auth/login or /auth/signup endpoint,
    //       store the session token, then redirect.
    await new Promise((r) => setTimeout(r, 600));
    router.push("/dashboard");
  }

  return (
    <div>
      <h1 className="text-xl font-semibold tracking-tight text-zinc-50">
        {isSignup ? "Create your account" : "Welcome back"}
      </h1>
      <p className="mt-1 text-sm text-zinc-400">
        {isSignup
          ? "Start benchmarking submissions in isolation."
          : "Log in to submit and track your runs."}
      </p>

      <form onSubmit={onSubmit} className="mt-6 space-y-4">
        {isSignup && (
          <Field
            label="Name"
            name="name"
            type="text"
            placeholder="Ada Lovelace"
            autoComplete="name"
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

        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded-lg bg-zinc-50 px-4 py-2.5 text-sm font-medium text-zinc-950 transition-colors hover:bg-zinc-200 disabled:opacity-60"
        >
          {submitting
            ? "Please wait…"
            : isSignup
              ? "Create account"
              : "Log in"}
        </button>
      </form>

      <div className="mt-5 text-center text-sm text-zinc-400">
        {isSignup ? (
          <>
            Already have an account?{" "}
            <Link href="/login" className="font-medium text-accent hover:underline">
              Log in
            </Link>
          </>
        ) : (
          <>
            New here?{" "}
            <Link href="/signup" className="font-medium text-accent hover:underline">
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
      <span className="mb-1.5 block text-sm font-medium text-zinc-300">
        {label}
      </span>
      <input
        {...props}
        className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-600 focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
      />
    </label>
  );
}
