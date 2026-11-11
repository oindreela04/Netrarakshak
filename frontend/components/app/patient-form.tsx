"use client";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Check, Field, Input, Select, Textarea } from "@/components/ui/input";

export type PatientInput = {
  first_name: string; last_name: string; date_of_birth: string; sex: string; phone: string; email: string; address: string;
  emergency_contact: string; abha_id: string; medical_history: string; has_diabetes: boolean; diabetes_type: string;
  diabetes_since_year: string; last_hba1c: string; has_hypertension: boolean; hypertension_since_year: string; medications: string;
};

export const emptyPatient: PatientInput = {
  first_name: "", last_name: "", date_of_birth: "", sex: "unspecified", phone: "", email: "", address: "", emergency_contact: "",
  abha_id: "", medical_history: "", has_diabetes: false, diabetes_type: "", diabetes_since_year: "", last_hba1c: "",
  has_hypertension: false, hypertension_since_year: "", medications: "",
};

export function toPayload(p: PatientInput) {
  const num = (s: string) => (s.trim() === "" ? null : Number(s));
  return { ...p, email: p.email || null, diabetes_since_year: num(p.diabetes_since_year), last_hba1c: num(p.last_hba1c),
    hypertension_since_year: num(p.hypertension_since_year) };
}

export function fromPatient(p: any): PatientInput {
  const s = (v: any) => (v == null ? "" : String(v));
  return Object.fromEntries(Object.keys(emptyPatient).map((k) => [k, typeof (emptyPatient as any)[k] === "boolean" ? !!p[k] : s(p[k])])) as PatientInput;
}

function age(dob: string) {
  if (!dob) return null;
  const d = new Date(dob), t = new Date();
  let a = t.getFullYear() - d.getFullYear();
  if (t.getMonth() < d.getMonth() || (t.getMonth() === d.getMonth() && t.getDate() < d.getDate())) a--;
  return a >= 0 && a < 130 ? a : null;
}

export function PatientFields({ v, set }: { v: PatientInput; set: (p: PatientInput) => void }) {
  const f = (k: keyof PatientInput) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => set({ ...v, [k]: e.target.value });
  const a = age(v.date_of_birth);
  return (
    <div className="space-y-8">
      <section>
        <h3 className="mb-4 text-sm font-semibold text-navy">Identity and contact</h3>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <Field label="First name"><Input required value={v.first_name} onChange={f("first_name")} /></Field>
          <Field label="Last name"><Input value={v.last_name} onChange={f("last_name")} /></Field>
          <Field label="Date of birth" hint={a != null ? `Age ${a} years` : undefined}><Input required type="date" max={new Date().toISOString().slice(0, 10)} value={v.date_of_birth} onChange={f("date_of_birth")} /></Field>
          <Field label="Sex"><Select value={v.sex} onChange={f("sex")}><option value="female">Female</option><option value="male">Male</option><option value="other">Other</option><option value="unspecified">Prefer not to say</option></Select></Field>
          <Field label="Mobile number"><Input value={v.phone} onChange={f("phone")} placeholder="+91" /></Field>
          <Field label="Email"><Input type="email" value={v.email} onChange={f("email")} /></Field>
          <Field label="Address" className="sm:col-span-2"><Input value={v.address} onChange={f("address")} /></Field>
          <Field label="ABHA ID" hint="Optional Ayushman Bharat Health Account"><Input value={v.abha_id} onChange={f("abha_id")} /></Field>
          <Field label="Emergency contact" className="sm:col-span-2 lg:col-span-1"><Input value={v.emergency_contact} onChange={f("emergency_contact")} /></Field>
        </div>
      </section>
      <section>
        <h3 className="mb-4 text-sm font-semibold text-navy">Medical history</h3>
        <div className="grid gap-4 lg:grid-cols-2">
          <div className="space-y-3 rounded-md border border-line p-4">
            <Check label="Diabetes mellitus" checked={v.has_diabetes} onChange={(x) => set({ ...v, has_diabetes: x })} />
            {v.has_diabetes && (
              <div className="grid gap-3 sm:grid-cols-3">
                <Field label="Type"><Select value={v.diabetes_type} onChange={f("diabetes_type")}><option value="">Unknown</option><option>Type 1</option><option>Type 2</option><option>Gestational</option><option>Other</option></Select></Field>
                <Field label="Diagnosed (year)"><Input inputMode="numeric" value={v.diabetes_since_year} onChange={f("diabetes_since_year")} /></Field>
                <Field label="Last HbA1c (%)"><Input inputMode="decimal" value={v.last_hba1c} onChange={f("last_hba1c")} /></Field>
              </div>
            )}
          </div>
          <div className="space-y-3 rounded-md border border-line p-4">
            <Check label="Hypertension" checked={v.has_hypertension} onChange={(x) => set({ ...v, has_hypertension: x })} />
            {v.has_hypertension && <Field label="Diagnosed (year)"><Input inputMode="numeric" value={v.hypertension_since_year} onChange={f("hypertension_since_year")} /></Field>}
          </div>
          <Field label="Relevant medications"><Textarea value={v.medications} onChange={f("medications")} placeholder="e.g. Metformin 500 mg BD, Amlodipine 5 mg OD" /></Field>
          <Field label="Other medical and ocular history"><Textarea value={v.medical_history} onChange={f("medical_history")} placeholder="Previous eye surgery, laser treatment, known eye conditions…" /></Field>
        </div>
      </section>
    </div>
  );
}

export const CONSENTS = [
  { key: "screening", label: "Retinal screening", desc: "Photography of both eyes and review by an ophthalmologist." },
  { key: "ai_analysis", label: "AI-assisted analysis", desc: "Analysis of the photographs by NetraRakshak's AI, reviewed by a clinician." },
  { key: "data_storage", label: "Secure storage of records", desc: "Storage of images and reports for the hospital's retention period." },
  { key: "research", label: "De-identified research use", desc: "Optional. Use of de-identified images to improve screening." },
];

export function ConsentChooser({ value, onChange }: { value: Record<string, boolean>; onChange: (v: Record<string, boolean>) => void }) {
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {CONSENTS.map((c) => (
        <div key={c.key} className="rounded-md border border-line p-3">
          <Check checked={!!value[c.key]} onChange={(x) => onChange({ ...value, [c.key]: x })}
            label={<><span className="font-medium text-navy">{c.label}</span><span className="block text-xs text-slate">{c.desc}</span></>} />
        </div>
      ))}
    </div>
  );
}

export function useSubmitting() {
  const [busy, setBusy] = useState(false);
  return { busy, run: async (fn: () => Promise<void>) => { setBusy(true); try { await fn(); } finally { setBusy(false); } } };
}
export { Button };
