"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { Columns2, Maximize, Minus, Plus, Square } from "lucide-react";
import { cn } from "@/lib/utils";
import { useSecureBlob, QualityBadge } from "./bits";

export type EyeView = {
  label: string;
  imagePath?: string;
  overlayPath?: string;
  heatmapPath?: string;
  quality?: string;
  qualitySummary?: string;
};

type Layer = "original" | "overlay" | "heatmap";
type Mode = "single" | "both" | "compare";

/**
 * Diagnostic-style viewer: zoom (wheel / buttons), pan (drag), fit-to-screen, layer switching
 * (original / Grad-CAM overlay / heatmap), right-and-left side-by-side and original-vs-explainability compare.
 * Zoom and pan are synchronised across panes.
 */
export function RetinalViewer({ right, left }: { right: EyeView; left: EyeView }) {
  const [eye, setEye] = useState<"right" | "left">(right.imagePath ? "right" : "left");
  const [mode, setMode] = useState<Mode>("single");
  const [layer, setLayer] = useState<Layer>("original");
  const [view, setView] = useState({ z: 1, x: 0, y: 0 });
  const eyes = { right, left };
  const cur = eyes[eye];
  const hasCam = !!(right.overlayPath || left.overlayPath);

  useEffect(() => { if (!hasCam && layer !== "original") setLayer("original"); }, [hasCam, layer]);
  const zoom = (f: number) => setView((v) => ({ ...v, z: Math.min(8, Math.max(1, v.z * f)) }));
  const fit = () => setView({ z: 1, x: 0, y: 0 });

  const pathFor = (e: EyeView, l: Layer) => (l === "overlay" ? e.overlayPath : l === "heatmap" ? e.heatmapPath : e.imagePath);
  const panes: { e: EyeView; l: Layer; title: string }[] =
    mode === "both" ? [{ e: right, l: layer, title: right.label }, { e: left, l: layer, title: left.label }]
      : mode === "compare" ? [{ e: cur, l: "original", title: `${cur.label} · original` }, { e: cur, l: "overlay", title: `${cur.label} · Grad-CAM` }]
        : [{ e: cur, l: layer, title: cur.label }];

  return (
    <div className="overflow-hidden rounded-lg border border-navy-700 bg-navy-900">
      <div className="flex flex-wrap items-center gap-2 border-b border-white/10 px-3 py-2">
        <Seg value={mode} onChange={(m) => { setMode(m as Mode); fit(); }} options={[["single", "Single", Square], ["both", "OD + OS", Columns2], ...(hasCam ? [["compare", "Compare", Columns2] as const] : [])]} />
        {mode !== "both" && <Seg value={eye} onChange={(e) => { setEye(e as any); fit(); }} options={[["right", "Right eye (OD)"], ["left", "Left eye (OS)"]]} />}
        {mode !== "compare" && hasCam && <Seg value={layer} onChange={(l) => setLayer(l as Layer)} options={[["original", "Original"], ["overlay", "Grad-CAM overlay"], ["heatmap", "Heatmap"]]} />}
        <div className="ml-auto flex items-center gap-1">
          <IconBtn label="Zoom out" onClick={() => zoom(1 / 1.4)}><Minus /></IconBtn>
          <span className="tabular w-12 text-center text-xs text-white/70">{Math.round(view.z * 100)}%</span>
          <IconBtn label="Zoom in" onClick={() => zoom(1.4)}><Plus /></IconBtn>
          <IconBtn label="Fit to screen" onClick={fit}><Maximize /></IconBtn>
        </div>
      </div>
      <div className={cn("grid gap-px bg-white/10", panes.length === 2 && "md:grid-cols-2")}>
        {panes.map((p, i) => <Pane key={i + p.title + p.l} {...p} path={pathFor(p.e, p.l)} view={view} setView={setView} />)}
      </div>
    </div>
  );
}

function Pane({ e, l, title, path, view, setView }: { e: EyeView; l: Layer; title: string; path?: string; view: { z: number; x: number; y: number }; setView: React.Dispatch<React.SetStateAction<{ z: number; x: number; y: number }>> }) {
  const { url, err } = useSecureBlob(path ?? null);
  const drag = useRef<{ x: number; y: number } | null>(null);
  const box = useRef<HTMLDivElement>(null);

  const onWheel = useCallback((ev: WheelEvent) => {
    ev.preventDefault();
    setView((v) => ({ ...v, z: Math.min(8, Math.max(1, v.z * (ev.deltaY < 0 ? 1.15 : 1 / 1.15))) }));
  }, [setView]);
  useEffect(() => {
    const el = box.current;
    if (!el) return;
    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel);
  }, [onWheel]);

  return (
    <div className="relative bg-black">
      <div ref={box} className={cn("relative aspect-square max-h-[560px] w-full select-none overflow-hidden", view.z > 1 ? "cursor-grab active:cursor-grabbing" : "")}
        onPointerDown={(ev) => { drag.current = { x: ev.clientX, y: ev.clientY }; (ev.target as Element).setPointerCapture?.(ev.pointerId); }}
        onPointerMove={(ev) => {
          if (!drag.current || view.z <= 1) return;
          const dx = ev.clientX - drag.current.x, dy = ev.clientY - drag.current.y;
          drag.current = { x: ev.clientX, y: ev.clientY };
          setView((v) => ({ ...v, x: v.x + dx / v.z, y: v.y + dy / v.z }));
        }}
        onPointerUp={() => (drag.current = null)}
        onDoubleClick={() => setView((v) => (v.z > 1 ? { z: 1, x: 0, y: 0 } : { ...v, z: 2.5 }))}>
        {!path ? <div className="flex h-full items-center justify-center text-sm text-white/50">{l === "original" ? "No photograph uploaded" : "No explainability map for this eye"}</div>
          : err ? <div className="flex h-full items-center justify-center text-sm text-white/50">Image could not be loaded</div>
            : !url ? <div className="h-full w-full animate-pulse bg-white/5" />
              // eslint-disable-next-line @next/next/no-img-element
              : <img src={url} alt={title} draggable={false} className="h-full w-full object-contain"
                style={{ transform: `scale(${view.z}) translate(${view.x}px, ${view.y}px)`, transition: drag.current ? "none" : "transform .12s ease-out" }} />}
      </div>
      <div className="pointer-events-none absolute inset-x-0 top-0 flex items-start justify-between gap-2 p-3">
        <span className="rounded bg-black/60 px-2 py-1 text-xs font-medium text-white">{title}</span>
        {e.quality && l === "original" && <span className="pointer-events-auto" title={e.qualitySummary}><QualityBadge verdict={e.quality} /></span>}
      </div>
      {l !== "original" && path && (
        <p className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/85 to-transparent px-3 pb-2.5 pt-6 text-[11.5px] leading-4 text-white/85">
          Model explainability. Highlighted regions influenced the AI output; they are not confirmed lesions or clinical findings.
        </p>
      )}
    </div>
  );
}

function Seg({ value, onChange, options }: { value: string; onChange: (v: string) => void; options: readonly (readonly [string, string, any?])[] }) {
  return (
    <div className="flex rounded-md bg-white/5 p-0.5">
      {options.map(([k, l, Icon]) => (
        <button key={k} onClick={() => onChange(k)} className={cn("flex items-center gap-1.5 rounded px-2.5 py-1 text-xs text-white/65 hover:text-white", value === k && "bg-white/15 font-medium text-white")}>
          {Icon && <Icon className="h-3.5 w-3.5" />}{l}
        </button>
      ))}
    </div>
  );
}

function IconBtn({ label, onClick, children }: { label: string; onClick: () => void; children: React.ReactNode }) {
  return <button aria-label={label} title={label} onClick={onClick} className="rounded p-1.5 text-white/70 hover:bg-white/10 hover:text-white [&_svg]:h-4 [&_svg]:w-4">{children}</button>;
}
