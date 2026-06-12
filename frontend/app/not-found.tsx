import Link from "next/link";

export default function NotFound() {
  return (
    <div className="grid-backdrop flex flex-1 flex-col items-center justify-center px-6 text-center">
      <p className="font-mono text-sm text-accent">404</p>
      <h1 className="mt-2 text-3xl font-semibold tracking-tight text-zinc-50">
        Not found
      </h1>
      <p className="mt-2 text-zinc-400">
        That run or page doesn&apos;t exist — or its container was destroyed.
      </p>
      <Link
        href="/dashboard"
        className="mt-6 rounded-lg bg-zinc-50 px-4 py-2 text-sm font-medium text-zinc-950 transition-colors hover:bg-zinc-200"
      >
        Back to dashboard
      </Link>
    </div>
  );
}
