"use client";
import { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";

/** Reveals children with a short 3D lift when they scroll into view (once). Honours reduced motion via CSS. */
export function Reveal({ children, className, delay = 0, as: Tag = "div" }: { children: React.ReactNode; className?: string; delay?: number; as?: any }) {
  const ref = useRef<HTMLElement>(null);
  const [shown, setShown] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const io = new IntersectionObserver(([e]) => { if (e.isIntersecting) { setShown(true); io.disconnect(); } }, { threshold: 0.15, rootMargin: "0px 0px -8% 0px" });
    io.observe(el);
    return () => io.disconnect();
  }, []);
  return <Tag ref={ref} className={cn("reveal", shown && "reveal-in", className)} style={{ transitionDelay: `${delay}ms` }}>{children}</Tag>;
}

/** Card that tilts in 3D under the pointer. */
export function Tilt({ children, className, max = 8 }: { children: React.ReactNode; className?: string; max?: number }) {
  const ref = useRef<HTMLDivElement>(null);
  const reset = () => { if (ref.current) ref.current.style.transform = "perspective(900px) rotateX(0deg) rotateY(0deg)"; };
  return (
    <div ref={ref} className={cn("tilt", className)} onPointerLeave={reset}
      onPointerMove={(e) => {
        if (window.matchMedia("(prefers-reduced-motion: reduce)").matches || e.pointerType !== "mouse") return;
        const r = e.currentTarget.getBoundingClientRect();
        const x = (e.clientX - r.left) / r.width - 0.5, y = (e.clientY - r.top) / r.height - 0.5;
        e.currentTarget.style.transform = `perspective(900px) rotateX(${-y * max}deg) rotateY(${x * max}deg) translateZ(0)`;
        e.currentTarget.style.setProperty("--gx", `${(x + 0.5) * 100}%`);
        e.currentTarget.style.setProperty("--gy", `${(y + 0.5) * 100}%`);
      }}>
      {children}
    </div>
  );
}

/** Headline that re-enters with stacked "echo" copies whenever `id` changes. */
export function EchoHeadline({ id, children, className }: { id: string | number; children: React.ReactNode; className?: string }) {
  return (
    <div key={id} className={cn("relative", className)}>
      <div aria-hidden className="echo echo-2 absolute inset-0">{children}</div>
      <div aria-hidden className="echo echo-1 absolute inset-0">{children}</div>
      <div className="echo-main relative">{children}</div>
    </div>
  );
}
