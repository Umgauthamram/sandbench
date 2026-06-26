import Link from "next/link";

export function Logo({ href = "/", gradient = false }: { href?: string; gradient?: boolean }) {
  return (
    <Link href={href} className="flex items-center gap-2.5 tracking-tight select-none">
      <span className={`text-3xl font-semibold ${gradient ? "text-transparent bg-clip-text bg-grad-accent" : "text-zinc-50"}`}>
        SandBench
      </span>
    </Link>
  );
}
