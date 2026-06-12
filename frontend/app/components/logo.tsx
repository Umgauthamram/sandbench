import Link from "next/link";

export function Logo({ href = "/" }: { href?: string }) {
  return (
    <Link href={href} className="flex items-center gap-2 font-semibold tracking-tight">
      <span className="grid h-7 w-7 place-items-center rounded-md bg-accent/15 ring-1 ring-accent/40">
        <span className="block h-3 w-3 rounded-sm bg-accent" />
      </span>
      <span className="text-zinc-50">
        Sand<span className="text-accent">Bench</span>
      </span>
    </Link>
  );
}
