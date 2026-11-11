import { cn } from "@/lib/utils";

export function Mark({ className, light }: { className?: string; light?: boolean }) {
  const ring = light ? "#FFFFFF" : "#0B1F3A";
  return (
    <svg viewBox="0 0 32 32" className={cn("h-8 w-8", className)} aria-hidden>
      <path d="M2 16c3.6-6.2 8.4-9.3 14-9.3S26.4 9.8 30 16c-3.6 6.2-8.4 9.3-14 9.3S5.6 22.2 2 16Z" fill="none" stroke={ring} strokeWidth="1.8" />
      <circle cx="16" cy="16" r="6.2" fill="#3E8E8A" />
      <path d="M13.2 16c1.1-1.6 2.5-2.4 4.1-2.4M16 19.6c1.3-.4 2.2-1.3 2.6-2.6" stroke="#fff" strokeWidth="1.2" fill="none" strokeLinecap="round" />
      <circle cx="18.6" cy="13.8" r="1.1" fill="#fff" />
    </svg>
  );
}

export function Logo({ light, className }: { light?: boolean; className?: string }) {
  return (
    <span className={cn("inline-flex items-center gap-2.5", className)}>
      <Mark light={light} />
      <span className={cn("text-[17px] font-bold tracking-tight", light ? "text-white" : "text-navy")}>
        Netra<span className={light ? "text-teal-100" : "text-teal"}>Rakshak</span>
      </span>
    </span>
  );
}
