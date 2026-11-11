"use client";
import { useState } from "react";
import { toast } from "sonner";
import { CheckCircle2 } from "lucide-react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Field, Input, Textarea } from "@/components/ui/input";

export function EnquiryForm({ kind }: { kind: "demo" | "contact" }) {
  const [f, setF] = useState({ name: "", organisation: "", email: "", phone: "", role: "", message: "" });
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState<string | null>(null);
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => setF({ ...f, [k]: e.target.value });

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      const r = await api<{ message: string }>("/public/enquiries", { method: "POST", json: { ...f, kind } });
      setDone(r.message);
    } catch (err: any) {
      toast.error(err.message);
    } finally { setBusy(false); }
  }

  if (done) return (
    <div className="flex items-start gap-3 rounded-lg border border-teal-100 bg-teal-50 p-6">
      <CheckCircle2 className="mt-0.5 h-5 w-5 text-teal" />
      <div><p className="font-semibold text-navy">{kind === "demo" ? "Demo request received" : "Message sent"}</p><p className="mt-1 text-sm text-slate">{done}</p></div>
    </div>
  );

  return (
    <form onSubmit={submit} className="grid gap-4 sm:grid-cols-2">
      <Field label="Your name"><Input required value={f.name} onChange={set("name")} autoComplete="name" /></Field>
      <Field label="Hospital or clinic"><Input required value={f.organisation} onChange={set("organisation")} autoComplete="organization" /></Field>
      <Field label="Work email"><Input required type="email" value={f.email} onChange={set("email")} autoComplete="email" /></Field>
      <Field label="Phone"><Input value={f.phone} onChange={set("phone")} autoComplete="tel" /></Field>
      <Field label="Your role" className="sm:col-span-2"><Input value={f.role} onChange={set("role")} placeholder="e.g. Medical director, ophthalmologist, IT head" /></Field>
      <Field label={kind === "demo" ? "What would you like to see?" : "Message"} className="sm:col-span-2">
        <Textarea value={f.message} onChange={set("message")} required={kind === "contact"} placeholder={kind === "demo" ? "Number of sites, fundus cameras in use, expected monthly screenings…" : ""} />
      </Field>
      <div className="sm:col-span-2 flex items-center justify-between gap-4">
        <p className="text-xs text-slate">We use these details only to respond to you. Please do not include patient information.</p>
        <Button type="submit" variant="primary" disabled={busy}>{busy ? "Sending…" : kind === "demo" ? "Request demo" : "Send message"}</Button>
      </div>
    </form>
  );
}
