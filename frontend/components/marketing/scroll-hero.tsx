"use client";
import Link from "next/link";
import { useEffect, useRef } from "react";
import { ChevronDown } from "lucide-react";
import { EyeScene } from "@/components/brand/eye-scene";
import { Button } from "@/components/ui/button";

/** Stage windows on the 0..1 scroll progress of the hero: [fade-in start, fully in, start fade-out, gone]. */
const STAGES: [number, number, number, number][] = [
  [-1, 0, 0.24, 0.32],
  [0.34, 0.42, 0.6, 0.68],
  [0.72, 0.8, 2, 3],
];

function opacityAt(p: number, [a, b, c, d]: [number, number, number, number]) {
  if (p <= a || p >= d) return 0;
  if (p < b) return (p - a) / (b - a);
  if (p > c) return 1 - (p - c) / (d - c);
  return 1;
}

export function ScrollHero() {
  const section = useRef<HTMLElement>(null);
  const progress = useRef({ current: 0 });
  const panels = useRef<(HTMLDivElement | null)[]>([]);
  const hint = useRef<HTMLDivElement>(null);
  const bar = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let raf = 0;
    const update = () => {
      raf = 0;
      const el = section.current;
      if (!el) return;
      const r = el.getBoundingClientRect();
      const total = el.offsetHeight - window.innerHeight;
      const p = Math.min(1, Math.max(0, -r.top / Math.max(total, 1)));
      progress.current.current = p;
      panels.current.forEach((node, i) => {
        if (!node) return;
        const o = opacityAt(p, STAGES[i]);
        node.style.opacity = String(o);
        node.style.transform = `translateY(${(1 - o) * 18}px)`;
        node.style.pointerEvents = o > 0.5 ? "auto" : "none";
        node.setAttribute("aria-hidden", o > 0.5 ? "false" : "true");
      });
      if (hint.current) hint.current.style.opacity = String(Math.max(0, 1 - p * 12));
      if (bar.current) bar.current.style.transform = `scaleY(${p})`;
    };
    const onScroll = () => { if (!raf) raf = requestAnimationFrame(update); };
    update();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    return () => { cancelAnimationFrame(raf); window.removeEventListener("scroll", onScroll); window.removeEventListener("resize", onScroll); };
  }, []);

  const panel = "absolute inset-x-0 top-[12vh] mx-auto max-w-6xl px-4 transition-none sm:px-6 lg:top-1/2 lg:-translate-y-1/2";
  const setRef = (i: number) => (n: HTMLDivElement | null) => { panels.current[i] = n; };

  return (
    <section ref={section} className="relative h-[340vh] bg-gradient-to-b from-white via-[#F4F8FC] to-white" aria-label="Introduction">
      <div className="sticky top-0 h-screen overflow-hidden">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(60%_55%_at_72%_50%,rgba(47,134,214,0.10),transparent_70%)]" />
        <EyeScene progress={progress.current} layout="hero" />

        <div className="pointer-events-none absolute inset-0">
          <div ref={setRef(0)} className={panel}>
            <div className="max-w-xl lg:max-w-[34rem]">
              <p className="text-sm font-semibold text-teal-700">Retinal screening platform for hospitals and eye clinics</p>
              <h1 className="mt-4 font-hero text-[46px] font-light leading-[1.02] text-navy sm:text-[68px]">See beyond the retina.</h1>
              <p className="mt-6 max-w-md text-[17px] leading-7 text-ink/75">
                NetraRakshak takes every fundus photograph from capture to a clinician-signed screening report.
              </p>
              <div className="mt-8 flex flex-wrap gap-3">
                <Button asChild size="lg" variant="primary"><Link href="/request-demo">Request a demo</Link></Button>
                <Button asChild size="lg" variant="outline" className="bg-white/70 backdrop-blur"><Link href="/#how">How it works</Link></Button>
              </div>
            </div>
          </div>

          <div ref={setRef(1)} className={panel} style={{ opacity: 0 }}>
            <div className="max-w-xl lg:max-w-[30rem]">
              <h2 className="font-hero text-[46px] font-light leading-[1.02] text-navy sm:text-[64px]">Detect earlier.</h2>
              <p className="mt-6 max-w-md text-[17px] leading-7 text-ink/75">
                Image quality is checked before any analysis. The diabetic retinopathy model then grades each eye, with calibrated
                confidence and a heatmap of the regions that shaped its suggestion.
              </p>
            </div>
          </div>

          <div ref={setRef(2)} className={panel} style={{ opacity: 0 }}>
            <div className="max-w-xl lg:max-w-[30rem]">
              <h2 className="font-hero text-[46px] font-light leading-[1.02] text-navy sm:text-[64px]">Protect vision.</h2>
              <p className="mt-6 max-w-md text-[17px] leading-7 text-ink/75">
                An ophthalmologist accepts, modifies or rejects every AI suggestion and signs the report. Uncertain cases are flagged
                for human review, never forced into a grade.
              </p>
              <div className="mt-8 flex flex-wrap gap-3">
                <Button asChild size="lg" variant="primary"><Link href="/request-demo">Request a demo</Link></Button>
                <Button asChild size="lg" variant="outline" className="bg-white/70 backdrop-blur"><Link href="/technology">About the AI</Link></Button>
              </div>
            </div>
          </div>
        </div>

        <div className="absolute right-5 top-1/2 hidden h-28 w-px -translate-y-1/2 bg-line lg:block" aria-hidden>
          <div ref={bar} className="h-full w-full origin-top bg-clinical" style={{ transform: "scaleY(0)" }} />
        </div>
        <div ref={hint} className="absolute bottom-8 left-1/2 flex -translate-x-1/2 flex-col items-center text-xs text-slate" aria-hidden>
          Scroll to explore<ChevronDown className="mt-1 h-4 w-4 animate-bounce" />
        </div>
      </div>
    </section>
  );
}
