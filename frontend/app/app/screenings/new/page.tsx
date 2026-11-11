"use client";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { toast } from "sonner";
import { Search } from "lucide-react";
import { api } from "@/lib/api";
import { useFetch } from "@/lib/use-fetch";
import { Button } from "@/components/ui/button";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { Field, Input, Select, Textarea } from "@/components/ui/input";
import { PageHeader, SyntheticTag } from "@/components/app/bits";
import { cn } from "@/lib/utils";

function NewScreeningInner() {
  const router = useRouter();
  const sp = useSearchParams();
  const [pid, setPid] = useState(sp.get("patient") ?? "");
  const [q, setQ] = useState("");
  const [dq, setDq] = useState("");
  const [camera, setCamera] = useState("");
  const [dilated, setDilated] = useState("");
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => { const t = setTimeout(() => setDq(q), 250); return () => clearTimeout(t); }, [q]);
  useEffect(() => { try { setCamera(localStorage.getItem("nr_camera") ?? ""); } catch {} }, []);
  const list = useFetch<any>(`/patients?page_size=8&q=${encodeURIComponent(dq)}`);
  const selected = useFetch<any>(pid ? `/patients/${pid}` : null, [pid]);

  async function start() {
    setBusy(true);
    try {
      try { localStorage.setItem("nr_camera", camera); } catch {}
      const s = await api<any>("/screenings", { method: "POST", json: { patient_id: pid, camera_device: camera, notes, dilated: dilated === "" ? null : dilated === "yes" } });
      router.push(`/app/screenings/${s.id}`);
    } catch (e: any) { toast.error(e.message); } finally { setBusy(false); }
  }

  const p = selected.data;
  return (
    <>
      <PageHeader title="New screening" description="Choose the patient, then capture both eyes on the fundus camera." />
      <div className="grid gap-6 lg:grid-cols-[1.1fr_1fr]">
        <Card>
          <CardHeader title="Patient" />
          <CardBody>
            <div className="relative"><Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate" />
              <Input className="pl-9" placeholder="Search by name, patient ID or mobile" value={q} onChange={(e) => setQ(e.target.value)} /></div>
            <ul className="mt-3 divide-y divide-line rounded-md border border-line">
              {list.data?.items.map((x: any) => (
                <li key={x.id}><button onClick={() => setPid(x.id)} className={cn("flex w-full items-center justify-between px-3 py-2.5 text-left text-sm hover:bg-mist", pid === x.id && "bg-clinical-50")}>
                  <span><span className="font-medium text-navy">{x.full_name}</span> {x.is_synthetic && <SyntheticTag />}<span className="block text-xs text-slate">{x.patient_code} · {x.age} y</span></span>
                  {pid === x.id && <span className="text-xs font-semibold text-clinical">Selected</span>}
                </button></li>
              ))}
              {list.data && !list.data.items.length && <li className="px-3 py-4 text-sm text-slate">No matching patients.</li>}
            </ul>
          </CardBody>
        </Card>
        <Card>
          <CardHeader title="Session details" />
          <CardBody className="space-y-4">
            {p ? (
              <div className="rounded-md bg-mist p-3 text-sm">
                <p className="font-semibold text-navy">{p.full_name} {p.is_synthetic && <SyntheticTag />}</p>
                <p className="text-xs text-slate">{p.patient_code} · {p.age} years · {p.has_diabetes ? "Diabetes" : "No diabetes recorded"}</p>
                {!p.consent_state.screening && <p className="mt-2 text-xs font-medium text-danger">Screening consent not recorded — record it on the patient profile first.</p>}
                {p.consent_state.screening && !p.consent_state.ai_analysis && <p className="mt-2 text-xs font-medium text-warn">No AI consent: images will be reviewed by the clinician without AI analysis.</p>}
              </div>
            ) : <p className="text-sm text-slate">Select a patient.</p>}
            <Field label="Fundus camera" hint="Make and model, remembered on this computer"><Input value={camera} onChange={(e) => setCamera(e.target.value)} placeholder="e.g. Topcon TRC-NW400" /></Field>
            <Field label="Pupil dilation"><Select value={dilated} onChange={(e) => setDilated(e.target.value)}><option value="">Not recorded</option><option value="yes">Dilated</option><option value="no">Undilated</option></Select></Field>
            <Field label="Notes"><Textarea value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Media opacity, cooperation, prior laser…" /></Field>
            <Button variant="primary" className="w-full" disabled={!pid || busy || (p && !p.consent_state.screening)} onClick={start}>{busy ? "Starting…" : "Start screening"}</Button>
          </CardBody>
        </Card>
      </div>
    </>
  );
}

export default function NewScreening() { return <Suspense><NewScreeningInner /></Suspense>; }
