"use client";
import Link from "next/link";
import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Lock } from "lucide-react";
import { api, tokens } from "@/lib/api";
import { Logo } from "@/components/brand/logo";
import { EyeScene } from "@/components/brand/eye-scene";
import { Button } from "@/components/ui/button";
import { Field, Input } from "@/components/ui/input";

function LoginForm() {
  const router = useRouter();
  const sp = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(sp.get("expired") ? "Your session ended. Please sign in again." : null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true); setError(null);
    try {
      const t = await api<{ access_token: string; refresh_token: string }>("/auth/login", { method: "POST", json: { email, password } });
      tokens.set(t.access_token, t.refresh_token);
      router.push("/app");
    } catch (err: any) {
      setError(err.message);
    } finally { setBusy(false); }
  }

  return (
    <form onSubmit={submit} className="space-y-4">
      <Field label="Work email"><Input type="email" required autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)} /></Field>
      <Field label="Password"><Input type="password" required autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} /></Field>
      {error && <p role="alert" className="rounded-md border border-[#F4CFCB] bg-[#FCEDEC] px-3 py-2 text-sm text-danger">{error}</p>}
      <Button type="submit" variant="primary" className="w-full rounded-full" size="lg" disabled={busy}>{busy ? "Signing in…" : "Sign in"}</Button>
    </form>
  );
}

export default function LoginPage() {
  return (
    <div className="grid min-h-screen bg-white lg:grid-cols-2">
      <div className="flex flex-col justify-between px-6 py-8 sm:px-12">
        <Link href="/"><Logo /></Link>
        <div className="mx-auto w-full max-w-sm py-12">
          <h1 className="font-hero text-[40px] font-light text-navy">Sign in</h1>
          <p className="mt-2 text-sm text-slate">For hospital staff with a NetraRakshak account. Accounts are created by your hospital administrator.</p>
          <div className="mt-8"><Suspense><LoginForm /></Suspense></div>
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
