import { cn } from "@/lib/utils";

const tones = {
  neutral: "bg-mist text-slate border-line",
  navy: "bg-navy text-white border-navy",
  blue: "bg-clinical-50 text-clinical-600 border-clinical-100",
  teal: "bg-teal-50 text-teal-700 border-teal-100",
  ok: "bg-[#EAF5EF] text-ok border-[#CFE7DA]",
  warn: "bg-[#FBF2E3] text-warn border-[#F0DDB8]",
  danger: "bg-[#FCEDEC] text-danger border-[#F4CFCB]",
};
export type Tone = keyof typeof tones;
export function Badge({ tone = "neutral", className, children }: { tone?: Tone; className?: string; children: React.ReactNode }) {
  return <span className={cn("inline-flex items-center gap-1 rounded-sm border px-1.5 py-0.5 text-[11.5px] font-semibold leading-4", tones[tone], className)}>{children}</span>;
}
