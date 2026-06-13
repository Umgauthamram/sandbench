import Link from "next/link";

export function Logo({ href = "/", gradient = false }: { href?: string; gradient?: boolean }) {
  return (
    <Link href={href} className="flex items-center gap-2.5 tracking-tight select-none">
          <span className="text-zinc-50 text-3xl font-semibold">
        SandBench
      </span>
    </Link>
  );
}
