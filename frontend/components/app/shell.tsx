"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import {
  Activity, BarChart3, Building2, ClipboardList, Cpu, CreditCard, FileText, LayoutDashboard, LogOut, Menu,
  ScrollText, Settings, Shield, Stethoscope, Users, UserSquare2, X,
} from "lucide-react";
import { Logo } from "@/components/brand/logo";
import { useAuth } from "@/lib/auth";
import { cn, ROLE_LABEL } from "@/lib/utils";

type Item = { href: string; label: string; icon: any; perm?: string; hospitalOnly?: boolean };
const GROUPS: { title?: string; items: Item[] }[] = [
  { items: [
    { href: "/app", label: "Dashboard", icon: LayoutDashboard, hospitalOnly: true },
    { href: "/app/patients", label: "Patients", icon: UserSquare2, perm: "patients.read" },
    { href: "/app/screenings", label: "Screenings", icon: Activity, perm: "screenings.read" },
    { href: "/app/review", label: "Review queue", icon: Stethoscope, perm: "review.write" },
    { href: "/app/reports", label: "Reports", icon: FileText, perm: "reports.read" },
    { href: "/app/analytics", label: "Analytics", icon: BarChart3, perm: "analytics.read" },
    { href: "/app/ai-models", label: "AI modules", icon: Cpu },
  ] },
  { title: "Administration", items: [
    { href: "/app/team", label: "Team", icon: Users, perm: "users.manage" },
    { href: "/app/hospital", label: "Hospital", icon: Building2, perm: "hospital.manage" },
    { href: "/app/subscription", label: "Subscription", icon: CreditCard, perm: "subscription.read", hospitalOnly: true },
    { href: "/app/audit", label: "Audit log", icon: ScrollText, perm: "audit.read" },
  ] },
  { title: "Platform", items: [{ href: "/app/platform", label: "Platform console", icon: Shield, perm: "platform.manage" }] },
  { items: [{ href: "/app/settings", label: "Account settings", icon: Settings }] },
];

export function Shell({ children }: { children: React.ReactNode }) {
  const { me, can, logout } = useAuth();
  const path = usePathname();
  const [open, setOpen] = useState(false);
  if (!me) return null;
  const visible = (i: Item) => (!i.perm || can(i.perm)) && (!i.hospitalOnly || !!me.hospital);

  const nav = (
    <nav className="flex-1 overflow-y-auto px-3 py-4">
      {GROUPS.map((g, gi) => {
        const items = g.items.filter(visible);
        if (!items.length) return null;
        return (
          <div key={gi} className="mb-5">
            {g.title && <p className="mb-1.5 px-3 text-[11.5px] font-medium text-slate">{g.title}</p>}
            {items.map((i) => {
              const active = i.href === "/app" ? path === "/app" : path.startsWith(i.href);
              return (
                <Link key={i.href} href={i.href} onClick={() => setOpen(false)}
                  className={cn("flex items-center gap-3 rounded-md px-3 py-2 text-[13.5px] text-ink/70 hover:bg-mist hover:text-navy",
                    active && "bg-clinical-50 font-semibold text-clinical-600")}>
                  <i.icon className="h-4 w-4" />{i.label}
                </Link>
              );
            })}
          </div>
        );
      })}
    </nav>
  );

  const side = (
    <div className="flex h-full flex-col border-r border-line bg-white">
      <div className="flex h-16 items-center border-b border-line px-5"><Link href="/app"><Logo /></Link></div>
      {me.hospital && (
        <div className="border-b border-line bg-mist/60 px-5 py-3">
          <p className="truncate text-[13px] font-semibold text-navy">{me.hospital.name}</p>
          <p className="text-[12px] text-slate">{me.hospital.plan_code.charAt(0) + me.hospital.plan_code.slice(1).toLowerCase()} plan · licence {me.hospital.licence_status}</p>
        </div>
      )}
      {nav}
      <div className="border-t border-line p-4">
        <p className="truncate text-[13px] font-medium text-navy">{me.user.full_name}</p>
        <p className="text-[12px] text-slate">{ROLE_LABEL[me.user.role]}</p>
        <button onClick={logout} className="mt-3 flex items-center gap-2 text-[13px] text-ink/70 hover:text-navy"><LogOut className="h-4 w-4" />Sign out</button>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-[#F6F8FB]">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 lg:block">{side}</aside>
      {open && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="absolute inset-0 bg-navy-900/50" onClick={() => setOpen(false)} />
          <div className="absolute inset-y-0 left-0 w-72">{side}</div>
        </div>
      )}
      <div className="lg:pl-64">
        <header className="sticky top-0 z-20 flex h-14 items-center gap-3 border-b border-line bg-white/95 px-4 backdrop-blur lg:hidden">
          <button onClick={() => setOpen(true)} aria-label="Open menu"><Menu className="h-5 w-5" /></button>
          <Logo />
        </header>
        {me.user.must_change_password && (
          <div className="border-b border-[#F0DDB8] bg-[#FBF2E3] px-6 py-2.5 text-sm text-warn">
            You are using a temporary password. <Link href="/app/settings" className="font-semibold underline">Set your own password</Link> before continuing clinical work.
          </div>
        )}
        <main className="mx-auto max-w-[1320px] px-4 py-8 sm:px-8">{children}</main>
        <footer className="mx-auto max-w-[1320px] px-4 pb-8 text-xs text-slate sm:px-8">
          NetraRakshak v0.9 · Investigational clinician-supervised screening aid · Not clinically validated or regulator-approved
        </footer>
      </div>
    </div>
  );
}
