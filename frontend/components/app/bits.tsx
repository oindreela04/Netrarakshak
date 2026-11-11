"use client";
import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { blobUrl } from "@/lib/api";
import { Badge, type Tone } from "@/components/ui/badge";
import { cn, STATUS_LABEL } from "@/lib/utils";

export function PageHeader({ title, description, actions }: { title: string; description?: React.ReactNode; actions?: React.ReactNode }) {
  return (
    <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <h1 className="font-display text-[30px] leading-tight text-navy">{title}</h1>
        {description && <div className="mt-1 text-sm text-slate">{description}</div>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </div>
  );
}

export function Loading({ label = "Loading" }: { label?: string }) {
  return <div className="flex items-center gap-2 py-12 text-sm text-slate"><Loader2 className="h-4 w-4 animate-spin" />{label}…</div>;
}

export function ErrorNote({ message }: { message: string }) {
  return <p role="alert" className="rounded-md border border-[#F4CFCB] bg-[#FCEDEC] px-4 py-3 text-sm text-danger">{message}</p>;
}

export function Empty({ title, body, action }: { title: string; body?: string; action?: React.ReactNode }) {
  return (
    <div className="flex flex-col items-center px-6 py-14 text-center">
      <p className="font-semibold text-navy">{title}</p>
      {body && <p className="mt-1 max-w-sm text-sm text-slate">{body}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

const STATUS_TONE: Record<string, Tone> = {
  draft: "neutral", quality_checked: "blue", analysed: "warn", in_review: "warn",
  recapture_requested: "danger", signed: "teal", reported: "ok",
};
export function StatusBadge({ status }: { status: string }) {
  return <Badge tone={STATUS_TONE[status] ?? "neutral"}>{STATUS_LABEL[status] ?? status}</Badge>;
}

export function QualityBadge({ verdict }: { verdict: string }) {
  const map: Record<string, [Tone, string]> = {
    acceptable: ["ok", "Acceptable"], recapture_required: ["danger", "Recapture required"],
    inconclusive: ["warn", "Inconclusive"], pending: ["neutral", "Pending"],
  };
  const [tone, label] = map[verdict] ?? ["neutral", verdict];
  return <Badge tone={tone}>{label}</Badge>;
}

export function SyntheticTag() {
  return <Badge tone="danger" className="font-bold">SYNTHETIC</Badge>;
}

export function Stat({ label, value, sub, className }: { label: string; value: React.ReactNode; sub?: React.ReactNode; className?: string }) {
  return (
    <div className={cn("rounded-lg border border-line bg-white px-5 py-4 shadow-panel", className)}>
      <p className="text-[13px] text-slate">{label}</p>
      <p className="tabular mt-1 text-[28px] font-semibold leading-none text-navy">{value}</p>
      {sub && <p className="mt-2 text-xs text-slate">{sub}</p>}
    </div>
  );
}

/** Image fetched with the user's bearer token (patient images are never public URLs). */
export function useSecureBlob(path: string | null) {
  const [url, setUrl] = useState<string | null>(null);
  const [err, setErr] = useState(false);
  useEffect(() => {
    let alive = true;
    let u: string | null = null;
    setUrl(null); setErr(false);
    if (path) blobUrl(path).then((x) => { u = x; if (alive) setUrl(x); else URL.revokeObjectURL(x); }).catch(() => alive && setErr(true));
    return () => { alive = false; if (u) URL.revokeObjectURL(u); };
  }, [path]);
  return { url, err };
}

export function SecureImage({ path, alt, className }: { path: string; alt: string; className?: string }) {
  const { url, err } = useSecureBlob(path);
  if (err) return <div className={cn("flex items-center justify-center bg-mist text-xs text-slate", className)}>Image unavailable</div>;
  if (!url) return <div className={cn("animate-pulse bg-navy/10", className)} />;
  // eslint-disable-next-line @next/next/no-img-element
  return <img src={url} alt={alt} className={className} />;
}
