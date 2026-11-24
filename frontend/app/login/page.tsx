"use client";
import Link from "next/link";
import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { ArrowRight, Building2, ClipboardList, Loader2, Lock, ScanEye, Stethoscope } from "lucide-react";
import { api, tokens } from "@/lib/api";
import { Logo } from "@/components/brand/logo";
import { EyeScene } from "@/components/brand/eye-scene";
import { Button } from "@/components/ui/button";
import { Field, Input } from "@/components/ui/input";

type DemoAccount = { role: string; label: string; description: string };
const DEMO_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  technician: ScanEye, ophthalmologist: Stethoscope, hospital_admin: Building2, receptionist: ClipboardList,
};

function friendly(err: any): string {
  if (err instanceof TypeError) return "Couldn't reach the server. It may still be waking up – please try again in a few seconds.";
  return err?.message || "Something went wrong. Please try again.";
}

function LoginForm() {
  const router = useRouter();
  const sp = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(sp.get("expired") ? "Your session ended. Please sign in again." : null);
  const [busy, setBusy] = useState<string | null>(null);
  const [demo, setDemo] = useState<DemoAccount[] | null>(null);
  const [waking, setWaking] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  // Ask the API which demo roles exist. On the free hosting plan this also wakes the server up.
  useEffect(() => {
    let done = false;
    const slow = setTimeout(() => { if (!done) setWaking(true); }, 2500);
    const load = async (attempt = 0): Promise<void> => {
      try {
        const r = await api<{ enabled: boolean; accounts: DemoAccount[] }>("/auth/demo-accounts");
        done = true; setWaking(false); setDemo(r.enabled ? r.accounts : []);
      } catch {
        if (attempt < 6) { setTimeout(() => load(attempt + 1), 8000); }
        else { done = true; setWaking(false); setDemo([]); }
      }
    };
    load();
    return () => { done = true; clearTimeout(slow); };
  }, []);

  const finish = (t: { access_token: string; refresh_token: string }) => { tokens.set(t.access_token, t.refresh_token); router.push("/app"); };

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy("form"); setError(null);
    try {
      finish(await api<{ access_token: string; refresh_token: string }>("/auth/login", { method: "POST", json: { email, password } }));
    } catch (err: any) { setError(friendly(err)); } finally { setBusy(null); }
  }

  async function demoLogin(role: string) {
    setBusy(role); setError(null);
    try {
      finish(await api<{ access_token: string; refresh_token: string }>("/auth/demo-login", { method: "POST", json: { role } }));
    } catch (err: any) { setError(friendly(err)); setBusy(null); }
  }

  const demoOn = demo === null || demo.length > 0;

  return (
    <div className="space-y-6">
      {waking && (
        <div role="status" className="flex items-start gap-2 rounded-md border border-[#CFE3F5] bg-[#EEF6FD] px-3 py-2.5 text-[13px] text-clinical-600">
          <Loader2 className="mt-0.5 h-4 w-4 shrink-0 animate-spin" />
          <span>Waking up the demo server. On the free hosting plan this can take up to a minute the first time.</span>
        </div>
      )}
      {error && <p role="alert" className="rounded-md border border-[#F4CFCB] bg-[#FCEDEC] px-3 py-2 text-sm text-danger">{error}</p>}

      {demoOn && (
        <section aria-labelledby="demo-h">
          <h2 id="demo-h" className="text-[13px] font-semibold uppercase tracking-wider text-teal-700">Explore the live demo</h2>
          <p className="mt-1 text-[13px] text-slate">Choose a role to sign in instantly. Synthetic patients only.</p>
          <div className="mt-3 grid gap-2 sm:grid-cols-2">
            {(demo ?? [{ role: "technician", label: "Screening technician", description: "" }, { role: "ophthalmologist", label: "Ophthalmologist", description: "" },
                       { role: "hospital_admin", label: "Hospital administrator", description: "" }, { role: "receptionist", label: "Receptionist", description: "" }]).map((a) => {
              const Icon = DEMO_ICONS[a.role] ?? ScanEye;
              return (
                <button key={a.role} type="button" disabled={demo === null || !!busy} onClick={() => demoLogin(a.role)}
                  className="group flex items-start gap-3 rounded-lg border border-line bg-white p-3 text-left transition hover:border-clinical hover:bg-clinical-50 disabled:cursor-wait disabled:opacity-60">
                  <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-clinical-50 text-clinical group-hover:bg-white">
                    {busy === a.role ? <Loader2 className="h-4 w-4 animate-spin" /> : <Icon className="h-4 w-4" />}
                  </span>
                  <span className="min-w-0">
                    <span className="flex items-center gap-1 text-sm font-semibold text-navy">{a.label}<ArrowRight className="h-3.5 w-3.5 opacity-0 transition group-hover:opacity-100" /></span>
                    {a.description && <span className="mt-0.5 block text-xs leading-snug text-slate">{a.description}</span>}
                  </span>
                </button>
              );
            })}
          </div>
        </section>
      )}

      {demoOn && !showPassword ? (
        <button type="button" onClick={() => setShowPassword(true)} className="w-full text-center text-sm font-medium text-clinical hover:underline">
          Have a staff account? Sign in with email and password
        </button>
      ) : (
        <form onSubmit={submit} className="space-y-4">
          {demoOn && <div className="flex items-center gap-3 text-xs text-slate"><span className="h-px flex-1 bg-line" />Staff sign-in<span className="h-px flex-1 bg-line" /></div>}
          <Field label="Work email"><Input type="email" required autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)} /></Field>
          <Field label="Password"><Input type="password" required autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} /></Field>
          <Button type="submit" variant="primary" className="w-full rounded-full" size="lg" disabled={!!busy}>{busy === "form" ? "Signing in…" : "Sign in"}</Button>
        </form>
      )}
    </div>
  );
}

export default function LoginPage() {
  return (
    <div className="grid min-h-screen bg-white lg:grid-cols-2">
      <div className="flex flex-col justify-between px-6 py-8 sm:px-12">
        <Link href="/"><Logo /></Link>
        <div className="mx-auto w-full max-w-md py-10">
          <h1 className="font-hero text-[40px] font-light text-navy">Sign in</h1>
          <p className="mt-2 text-sm text-slate">Try the screening workflow with a demo role, or sign in with your hospital staff account.</p>
          <div className="mt-7"><Suspense><LoginForm /></Suspense></div>
          <p className="mt-6 flex items-center gap-2 text-xs text-slate"><Lock className="h-3.5 w-3.5" /> Access is logged. Sessions end when you close the browser tab.</p>
        </div>
        <p className="text-xs text-slate">New to NetraRakshak? <Link className="text-clinical hover:underline" href="/request-demo">Request a demo</Link></p>
      </div>
      <div className="relative hidden overflow-hidden border-l border-line bg-gradient-to-br from-[#F4F8FC] via-white to-teal-50 lg:block">
        <EyeScene layout="panel" />
        <p className="absolute inset-x-12 bottom-12 font-hero text-[24px] font-light leading-snug text-navy">
          Every AI result is a suggestion. Every report carries a clinician&apos;s signature.
        </p>
      </div>
    </div>
  );
}
