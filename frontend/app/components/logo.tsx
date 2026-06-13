import Link from "next/link";

export function Logo({ href = "/", gradient = false }: { href?: string; gradient?: boolean }) {
  return (
    <Link href={href} className="flex items-center gap-2.5 tracking-tight select-none">
      <span className={`grid h-8 w-8 place-items-center rounded-lg ring-1 transition-all ${
        gradient 
          ? "bg-grad-accent ring-orange-500/50 shadow-sm" 
          : "bg-accent/15 ring-accent/40"
      }`}>
        <span className={`block h-3.5 w-3.5 rounded-sm ${gradient ? "bg-white" : "bg-accent"}`} />
      </span>
      <span className="text-zinc-50 text-lg font-semibold">
        Sand<span className={gradient ? "text-grad-accent font-extrabold" : "text-accent font-bold"}>Bench</span>
      </span>
    </Link>
  );
}
