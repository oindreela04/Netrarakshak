"use client";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { Check } from "@/components/ui/input";
import { PageHeader } from "@/components/app/bits";
import { Button, ConsentChooser, emptyPatient, PatientFields, toPayload, useSubmitting } from "@/components/app/patient-form";

export default function NewPatient() {
  const router = useRouter();
  const [v, setV] = useState(emptyPatient);
  const [consent, setConsent] = useState<Record<string, boolean>>({ screening: true, ai_analysis: true, data_storage: true, research: false });
  const [method, setMethod] = useState("written");
  const [synthetic, setSynthetic] = useState(false);
  const { busy, run } = useSubmitting();

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    run(async () => {
      try {
        const p = await api<any>("/patients", { method: "POST", json: { ...toPayload(v), is_synthetic: synthetic,
          consents: Object.entries(consent).map(([consent_type, granted]) => ({ consent_type, granted, method })) } });
        toast.success(`Registered ${p.full_name} · ${p.patient_code}`);
        router.push(`/app/patients/${p.id}`);
      } catch (err: any) { toast.error(err.message); }
    });
  };

  return (
    <form onSubmit={submit}>
      <PageHeader title="Register patient" description="A unique patient ID is assigned automatically." />
      <div className="space-y-6">
        <Card><CardBody><PatientFields v={v} set={setV} /></CardBody></Card>
        <Card>
          <CardHeader title="Consent" description="Record what the patient has agreed to. Screening cannot start without screening consent; AI analysis does not run without AI consent." />
          <CardBody className="space-y-4">
            <ConsentChooser value={consent} onChange={setConsent} />
            <div className="flex flex-wrap items-center gap-6 text-sm">
              <span className="text-slate">Consent obtained by</span>
              {[["written", "Signed form"], ["digital", "Digital signature"], ["verbal_witnessed", "Verbal, witnessed"]].map(([k, l]) => (
                <label key={k} className="flex items-center gap-2"><input type="radio" name="method" className="accent-[#1F6FB2]" checked={method === k} onChange={() => setMethod(k)} />{l}</label>
              ))}
            </div>
          </CardBody>
        </Card>
        <div className="flex flex-col-reverse items-start justify-between gap-4 sm:flex-row sm:items-center">
          <Check checked={synthetic} onChange={setSynthetic} label={<span className="text-sm text-slate">This is a synthetic test record, not a real person (for training and demos)</span>} />
          <div className="flex gap-2">
            <Button type="button" variant="outline" onClick={() => router.back()}>Cancel</Button>
            <Button type="submit" variant="primary" disabled={busy}>{busy ? "Registering…" : "Register patient"}</Button>
          </div>
        </div>
      </div>
    </form>
  );
}
