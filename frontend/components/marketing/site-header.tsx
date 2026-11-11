"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { Menu, X } from "lucide-react";
import { Logo } from "@/components/brand/logo";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/#how", label: "How it works" },
  { href: "/technology", label: "AI technology" },
  { href: "/solutions", label: "For hospitals" },
  { href: "/security", label: "Security & privacy" },
  { href: "/contact", label: "Contact" },
];

export function SiteHeader() {
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    const on = () => setScrolled(window.scrollY > 8);
    on();
    window.addEventListener("scroll", on, { passive: true });
    return () => window.removeEventListener("scroll", on);
  }, []);
  return (
    <header className={cn("fixed inset-x-0 top-0 z-30 transition-[background-color,border-color,box-shadow] duration-300",
      scrolled || open ? "border-b border-line bg-white/85 shadow-[0_1px_12px_rgba(11,31,58,0.05)] backdrop-blur-md" : "border-b border-transparent bg-white/50 backdrop-blur-sm")}>
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
        <Link href="/" aria-label="NetraRakshak home"><Logo /></Link>
        <nav className="hidden items-center gap-7 lg:flex">
          {NAV.map((n) => <Link key={n.href} href={n.href} className="text-sm text-ink/70 hover:text-navy">{n.label}</Link>)}
        </nav>
        <div className="hidden items-center gap-2 lg:flex">
          <Button asChild variant="ghost"><Link href="/login">Sign in</Link></Button>
          <Button asChild variant="primary" className="rounded-full px-5"><Link href="/request-demo">Request a demo</Link></Button>
        </div>
        <button className="text-navy lg:hidden" onClick={() => setOpen(!open)} aria-label="Menu" aria-expanded={open}>{open ? <X /> : <Menu />}</button>
      </div>
      {open && (
        <div className="border-t border-line bg-white px-4 pb-4 lg:hidden">
          {NAV.map((n) => <Link key={n.href} href={n.href} onClick={() => setOpen(false)} className="block py-2.5 text-ink/85">{n.label}</Link>)}
          <div className="mt-3 flex gap-2">
            <Button asChild variant="outline" className="flex-1"><Link href="/login">Sign in</Link></Button>
            <Button asChild variant="primary" className="flex-1 rounded-full"><Link href="/request-demo">Request a demo</Link></Button>
          </div>
        </div>
      )}
    </header>
  );
}
