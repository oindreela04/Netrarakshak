"use client";
import { useRef, useState } from "react";
import { AlertTriangle, CheckCircle2, CircleDashed, ImageUp, RefreshCw, XCircle } from "lucide-react";
import { cn, pct } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { QualityBadge, SecureImage } from "./bits";

export const KEYS = ["no_dr", "mild_npdr", "moderate_npdr", "severe_npdr", "proliferative_dr"];
export const KEY_LABEL: Record<string, string> = {
  no_dr: "No apparent DR", mild_npdr: "Mild NPDR", moderate_npdr: "Moderate NPDR", severe_npdr: "Severe NPDR", proliferative_dr: "Proliferative DR",
};

/** Drag-and-drop upload slot for one eye. */
export function EyeDrop({ eye, image, screeningId, disabled, onFile, busy }: {
  eye: "right" | "left"; image?: any; screeningId: string; disabled?: boolean; busy?: boolean; onFile: (f: File) => void;
}) {
  const input = useRef<HTMLInputElement>(null);
  const [over, setOver] = useState(false);
  const label = eye === "right" ? "Right eye (OD)" : "Left eye (OS)";
  const pick = (files: FileList | null) => { const f = files?.[0]; if (f) onFile(f); };
  return (
    <div
      onDragOver={(e) => { e.preventDefault(); if (!disabled) setOver(true); }}
      onDragLeave={() => setOver(false)}
      onDrop={(e) => { e.preventDefault(); setOver(false); if (!disabled) pick(e.dataTransfer.files); }}
      className={cn("relative overflow-hidden rounded-lg border-2 border-dashed bg-white transition-colors", over ? "border-clinical bg-clinical-50" : "border-line")}>
      <input ref={input} type="file" hidden accept=".jpg,.jpeg,.png,.tif,.tiff,image/jpeg,image/png,image/tiff" onChange={(e) => { pick(e.target.files); e.target.value = ""; }} />
      <div className="flex items-center justify-between border-b border-line px-4 py-2.5">
        <p className="text-sm font-semibold text-navy">{label}</p>
        {image && <QualityBadge verdict={image.quality_verdict} />}
      </div>
      {image ? (
        <div className="grid grid-cols-[120px_1fr] gap-4 p-4">
          <SecureImage path={`/screenings/${screeningId}/images/${image.id}/file`} alt={label} className="aspect-square w-[120px] rounded bg-black object-contain" />
          <div className="min-w-0 text-xs text-slate">
            <p className="truncate font-medium text-ink" title={image.original_filename}>{image.original_filename}</p>
            <p className="mt-1">{image.width}×{image.height}px · {(image.file_size / 1024 / 1024).toFixed(2)} MB · {image.content_type.split("/")[1].toUpperCase()}</p>
            {image.metadata?.exif_Model && <p>Camera: {image.metadata.exif_Make} {image.metadata.exif_Model}</p>}
            <p className="mt-2 leading-5 text-ink/80">{image.quality?.summary}</p>
            {!disabled && <button onClick={() => input.current?.click()} disabled={busy} className="mt-2 inline-flex items-center gap-1 font-semibold text-clinical hover:underline"><RefreshCw className="h-3.5 w-3.5" />Replace image</button>}
          </div>
        </div>
      ) : (
        <button type="button" disabled={disabled || busy} onClick={() => input.current?.click()} className="flex w-full flex-col items-center px-6 py-10 text-center disabled:opacity-50">
          <ImageUp className="h-8 w-8 text-clinical" />
          <p className="mt-3 text-sm font-medium text-navy">{busy ? "Uploading and checking quality…" : "Drop the fundus photograph here or choose a file"}</p>
          <p className="mt-1 text-xs text-slate">JPEG, PNG or TIFF from a retinal fundus camera · up to 40 MB</p>
        </button>
      )}
      {busy && <div className="absolute inset-x-0 bottom-0 h-0.5 animate-pulse bg-clinical" />}
    </div>
  );
}

export function QualityChecks({ quality }: { quality: any }) {
  if (!quality?.checks) return null;
  const icon = (s: string) => s === "pass" ? <CheckCircle2 className="h-4 w-4 text-ok" /> : s === "warn" ? <AlertTriangle className="h-4 w-4 text-warn" /> : <XCircle className="h-4 w-4 text-danger" />;
  return (
    <ul className="divide-y divide-line text-sm">
      {quality.checks.map((c: any) => (
        <li key={c.key} className="flex items-start gap-3 py-2">
          <span className="mt-0.5">{icon(c.status)}</span>
          <div className="min-w-0 flex-1"><p className="font-medium text-ink">{c.label}</p><p className="text-xs text-slate">{c.message}</p></div>
        </li>
      ))}
      <li className="pt-2 text-[11px] text-slate">{quality.method}</li>
    </ul>
  );
}

const STATUS_COPY: Record<string, string> = {
  model_unavailable: "No AI model is active", quality_rejected: "Not analysed: image quality", consent_missing: "Not analysed: no AI consent", error: "Analysis failed",
};

/** Unmodified model output for one eye. */
export function AIResultCard({ r, eye }: { r?: any; eye: "right" | "left" }) {
  const label = eye === "right" ? "Right eye (OD)" : "Left eye (OS)";
  if (!r) return (
    <div className="rounded-lg border border-line bg-white p-4"><p className="text-sm font-semibold text-navy">{label}</p>
      <p className="mt-2 flex items-center gap-2 text-sm text-slate"><CircleDashed className="h-4 w-4" />AI analysis not run yet</p></div>
  );
  const inconclusive = r.status !== "completed" || r.is_uncertain;
  return (
    <div className={cn("rounded-lg border bg-white", inconclusive ? "border-[#F0DDB8]" : "border-line")}>
      <div className="flex items-center justify-between border-b border-line px-4 py-2.5">
        <p className="text-sm font-semibold text-navy">{label}</p>
        {r.status === "completed" ? <Badge tone="blue">Model v{r.model_version}</Badge> : <Badge tone="warn">{STATUS_COPY[r.status] ?? r.status}</Badge>}
      </div>
      <div className="p-4">
        <p className={cn("text-[15px] font-semibold", inconclusive ? "text-warn" : "text-navy")}>{r.display_verdict}</p>
        <p className="mt-1 text-xs leading-5 text-slate">{r.explanation}</p>
        {r.status === "completed" && (
          <>
            <div className="mt-4 space-y-1.5">
              {KEYS.map((k, i) => {
                const v = r.probabilities?.[k] ?? 0;
                const top = i === r.predicted_index;
                return (
                  <div key={k} className="grid grid-cols-[120px_1fr_48px] items-center gap-2 text-xs">
                    <span className={top ? "font-semibold text-navy" : "text-slate"}>{KEY_LABEL[k]}</span>
                    <div className="h-2 overflow-hidden rounded-full bg-mist"><div className={cn("h-full rounded-full", top ? "bg-clinical" : "bg-navy/25")} style={{ width: `${v * 100}%` }} /></div>
                    <span className="tabular text-right text-slate">{pct(v)}</span>
                  </div>
                );
              })}
            </div>
            <p className="mt-3 text-[11px] text-slate">Confidence {pct(r.confidence)} · normalised entropy {r.normalized_entropy?.toFixed(2)} · {r.inference_ms} ms · {r.model_name}</p>
          </>
        )}
      </div>
    </div>
  );
}
