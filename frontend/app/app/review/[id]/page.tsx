"use client";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Camera, PenLine, Save } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useFetch } from "@/lib/use-fetch";
import { cn, GRADE_LABEL } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { Check, Field, Input, Select, Textarea } from "@/components/ui/input";
import { ErrorNote, Loading, PageHeader, StatusBadge, SyntheticTag } from "@/components/app/bits";
import { RetinalViewer } from "@/components/app/retinal-viewer";
import { AIResultCard, KEYS } from "@/components/app/screening-parts";

type Eye = { ai_decision: string; final_grade: string; macular_oedema_suspected: boolean | null; other_findings: string; observations: string };
const blankEye: Eye = { ai_decision: "not_applicable", final_grade: "not_assessed", macular_oedema_suspected: null, other_findings: "", observations: "" };

export default function ReviewWorkspace() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { me } = useAuth();
  const { data: s, error, loading, reload } = useFetch<any>(`/screenings/${id}`);
  const patient = useFetch<any>(s ? `/patients/${s.patient.id}` : null, [s?.patient.id]);
  const [eyes, setEyes] = useState<Record<string, Eye>>({ right: { ...blankEye }, left: { ...blankEye } });
  const [form, setForm] = useState({ overall_impression: "", recommendations: "", referral_recommended: false, referral_urgency: "", referral_to: "", follow_up_months: "12" });
  const [signOpen, setSignOpen] = useState(false);
  const [recapOpen, setRecapOpen] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!s) return;
    const draft = [...s.reviews].reverse().find((r: any) => r.status === "draft" && r.reviewer_id === me?.user.id);
    if (draft) {
      setEyes({ right: { ...blankEye, ...draft.eye_findings.right }, left: { ...blankEye, ...draft.eye_findings.left } });
      setForm({ overall_impression: draft.overall_impression, recommendations: draft.recommendations, referral_recommended: draft.referral_recommended,
        referral_urgency: draft.referral_urgency, referral_to: draft.referral_to, follow_up_months: draft.follow_up_months?.toString() ?? "" });
    }
  }, [s, me]);

  if (loading && !s) return <Loading />;
  if (error) return <ErrorNote message={error} />;
  if (!s) return null;
  const ai = (e: string) => s.ai_results.find((r: any) => r.eye === e);
  const img = (e: string) => s.images.find((i: any) => i.eye === e);
  const locked = ["signed", "reported"].includes(s.status);
  const p = patient.data;

  const payload = () => ({
    eye_findings: Object.fromEntries((["right", "left"] as const).filter((e) => img(e)).map((e) => [e, eyes[e]])),
    ...form, follow_up_months: form.follow_up_months === "" ? null : Number(form.follow_up_months),
  });
  async function save(quiet = false) {
    setSaving(true);
    try { await api(`/reviews/screening/${id}`, { method: "PUT", json: payload() }); if (!quiet) toast.success("Draft saved"); return true; }
    catch (e: any) { toast.error(e.message); return false; } finally { setSaving(false); }
  }

  const setEye = (e: string, patch: Partial<Eye>) => setEyes((x) => ({ ...x, [e]: { ...x[e], ...patch } }));
  const decide = (e: string, d: string) => {
    const r = ai(e);
    if (d === "accept" && r?.predicted_index != null) setEye(e, { ai_decision: d, final_grade: KEYS[r.predicted_index] });
    else setEye(e, { ai_decision: d });
  };

  const view = (eye: "right" | "left") => {
    const i = img(eye), r = ai(eye);
    return { label: eye === "right" ? "Right eye (OD)" : "Left eye (OS)", imagePath: i ? `/screenings/${id}/images/${i.id}/file` : undefined,
      overlayPath: r?.has_gradcam ? `/screenings/${id}/ai/${r.id}/overlay` : undefined, heatmapPath: r?.has_gradcam ? `/screenings/${id}/ai/${r.id}/heatmap` : undefined,
      quality: i?.quality_verdict, qualitySummary: i?.quality?.summary };
  };

  return (
    <>
      <PageHeader title="Clinical review" description={<div className="flex flex-wrap items-center gap-2"><span>{s.patient.full_name}</span><span>·</span>
        <Link href={`/app/screenings/${id}`} className="text-clinical hover:underline">{s.screening_code}</Link><StatusBadge status={s.status} />{s.patient.is_synthetic && <SyntheticTag />}</div>}
        actions={!locked && <>
          <Button variant="outline" onClick={() => setRecapOpen(true)}><Camera />Request recapture</Button>
          <Button variant="outline" disabled={saving} onClick={() => save()}><Save />Save draft</Button>
          <Button variant="teal" onClick={async () => { if (await save(true)) setSignOpen(true); }}><PenLine />Approve and sign</Button>
        </>} />
      {locked && <p className="mb-5 rounded-md border border-teal-100 bg-teal-50 px-4 py-2.5 text-sm text-teal-700">This screening has been signed and is locked. <Link className="font-semibold underline" href={`/app/screenings/${id}`}>Open the screening</Link> to generate or view reports.</p>}

      <div className="grid gap-6 xl:grid-cols-[1.25fr_1fr]">
        <div className="space-y-6">
          <RetinalViewer right={view("right")} left={view("left")} />
          <Card>
            <CardHeader title="Patient" />
            <CardBody className="grid gap-x-8 gap-y-2 text-sm sm:grid-cols-2">
              <Row k="Age / sex" v={`${s.patient.age} years, ${s.patient.sex}`} />
              <Row k="Diabetes" v={p ? (p.has_diabetes ? [p.diabetes_type, p.diabetes_since_year && `since ${p.diabetes_since_year}`, p.last_hba1c && `HbA1c ${p.last_hba1c}%`].filter(Boolean).join(", ") || "Yes" : "No") : "…"} />
              <Row k="Hypertension" v={p ? (p.has_hypertension ? "Yes" : "No") : "…"} />
              <Row k="Medications" v={p?.medications} />
              <Row k="History" v={p?.medical_history} />
              <Row k="Session notes" v={[s.camera_device, s.dilated === true ? "dilated" : s.dilated === false ? "undilated" : "", s.notes].filter(Boolean).join(" · ")} />
            </CardBody>
          </Card>
        </div>

        <div className="space-y-6">
          <div>
            <p className="mb-2 text-[13px] font-semibold text-navy">Original AI output <span className="font-normal text-slate">— kept unchanged; your interpretation is recorded separately</span></p>
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-1 2xl:grid-cols-2">
              <AIResultCard eye="right" r={ai("right")} /><AIResultCard eye="left" r={ai("left")} />
            </div>
          </div>
          {(["right", "left"] as const).filter((e) => img(e)).map((e) => {
            const r = ai(e), has = r?.status === "completed", v = eyes[e];
            return (
              <Card key={e}>
                <CardHeader title={`Your interpretation · ${e === "right" ? "right eye (OD)" : "left eye (OS)"}`} />
                <CardBody className="space-y-4">
                  {has ? (
                    <div className="flex gap-2">
                      {[["accept", "Accept AI"], ["modify", "Modify"], ["reject", "Reject AI"]].map(([k, l]) => (
                        <button key={k} disabled={locked} onClick={() => decide(e, k)} className={cn("flex-1 rounded-md border px-3 py-2 text-sm font-medium",
                          v.ai_decision === k ? (k === "reject" ? "border-danger bg-[#FCEDEC] text-danger" : "border-clinical bg-clinical-50 text-clinical-600") : "border-line text-slate hover:bg-mist")}>{l}</button>
                      ))}
                    </div>
                  ) : <p className="text-xs text-slate">No completed AI finding for this eye. Grade from the image directly.</p>}
                  <Field label="Final grade">
                    <Select disabled={locked || v.ai_decision === "accept"} value={v.final_grade} onChange={(x) => setEye(e, { final_grade: x.target.value })}>
                      {Object.entries(GRADE_LABEL).map(([k, l]) => <option key={k} value={k}>{l}</option>)}
                    </Select>
                  </Field>
                  <Field label="Diabetic macular oedema suspected?">
                    <Select disabled={locked} value={v.macular_oedema_suspected == null ? "" : String(v.macular_oedema_suspected)} onChange={(x) => setEye(e, { macular_oedema_suspected: x.target.value === "" ? null : x.target.value === "true" })}>
                      <option value="">Not assessed</option><option value="false">No</option><option value="true">Yes</option>
                    </Select>
                  </Field>
                  <Field label="Other findings"><Input disabled={locked} value={v.other_findings} onChange={(x) => setEye(e, { other_findings: x.target.value })} placeholder="e.g. disc cupping, drusen, laser scars" /></Field>
                  <Field label="Observations"><Textarea disabled={locked} value={v.observations} onChange={(x) => setEye(e, { observations: x.target.value })} /></Field>
                </CardBody>
              </Card>
            );
          })}
          <Card>
            <CardHeader title="Impression and plan" />
            <CardBody className="space-y-4">
              <Field label="Overall impression"><Textarea disabled={locked} value={form.overall_impression} onChange={(e) => setForm({ ...form, overall_impression: e.target.value })} /></Field>
              <Field label="Recommendations (printed on the report)"><Textarea disabled={locked} value={form.recommendations} onChange={(e) => setForm({ ...form, recommendations: e.target.value })} /></Field>
              <Check disabled={locked} label="Recommend referral" checked={form.referral_recommended} onChange={(x) => setForm({ ...form, referral_recommended: x, referral_urgency: x ? form.referral_urgency || "routine" : "" })} />
              {form.referral_recommended && (
                <div className="grid gap-3 sm:grid-cols-2">
                  <Field label="Urgency"><Select disabled={locked} value={form.referral_urgency} onChange={(e) => setForm({ ...form, referral_urgency: e.target.value })}><option value="routine">Routine</option><option value="soon">Soon (within 4 weeks)</option><option value="urgent">Urgent</option></Select></Field>
                  <Field label="Refer to"><Input disabled={locked} value={form.referral_to} onChange={(e) => setForm({ ...form, referral_to: e.target.value })} placeholder="Retina clinic" /></Field>
                </div>
              )}
              <Field label="Next screening in (months)"><Input disabled={locked} inputMode="numeric" value={form.follow_up_months} onChange={(e) => setForm({ ...form, follow_up_months: e.target.value })} /></Field>
            </CardBody>
          </Card>
        </div>
      </div>

      <SignDialog open={signOpen} onClose={() => setSignOpen(false)} name={me?.user.full_name ?? ""} reg={me?.user.medical_registration_no ?? ""} eyes={eyes} has={(e) => !!img(e)}
        onSign={async (password) => {
          try { await api(`/reviews/screening/${id}/sign`, { method: "POST", json: { password, attestation: true } }); toast.success("Review signed"); router.push(`/app/screenings/${id}`); }
          catch (e: any) { toast.error(e.message); }
        }} />
      <RecaptureDialog open={recapOpen} onClose={() => setRecapOpen(false)} onSubmit={async (reason, eyesSel) => {
        try { await api(`/reviews/screening/${id}/request-recapture`, { method: "POST", json: { reason, eyes: eyesSel } }); toast.success("Recapture requested"); setRecapOpen(false); reload(); }
        catch (e: any) { toast.error(e.message); }
      }} />
    </>
  );
}

function Row({ k, v }: { k: string; v?: string }) {
  return <div className="flex justify-between gap-4 border-b border-line/70 py-1.5"><span className="text-slate">{k}</span><span className="text-right">{v || "—"}</span></div>;
}

function SignDialog({ open, onClose, onSign, name, reg, eyes, has }: { open: boolean; onClose: () => void; onSign: (pw: string) => void; name: string; reg: string; eyes: Record<string, Eye>; has: (e: string) => boolean }) {
  const [pw, setPw] = useState("");
  const [att, setAtt] = useState(false);
  return (
    <Dialog open={open} onOpenChange={(o) => { if (!o) { setPw(""); setAtt(false); onClose(); } }} title="Approve and sign"
      description="Signing locks this screening and allows a clinician-approved report to be issued.">
      <div className="space-y-4">
        <div className="rounded-md bg-mist p-3 text-sm">
          {(["right", "left"] as const).filter(has).map((e) => <p key={e}><span className="text-slate">{e === "right" ? "OD" : "OS"}: </span><b>{GRADE_LABEL[eyes[e].final_grade]}</b> <Badge>{eyes[e].ai_decision.replace("_", " ")}</Badge></p>)}
          <p className="mt-2 text-xs text-slate">{name} · Reg. No. {reg || <span className="text-danger">missing — ask your administrator</span>}</p>
        </div>
        <Check checked={att} onChange={setAtt} label="I have personally reviewed the retinal images, the AI output and its limitations, and this interpretation is my own clinical judgement." />
        <Field label="Your password"><Input type="password" autoComplete="current-password" value={pw} onChange={(e) => setPw(e.target.value)} /></Field>
        <div className="flex justify-end gap-2"><Button variant="outline" onClick={onClose}>Cancel</Button><Button variant="teal" disabled={!att || !pw} onClick={() => onSign(pw)}>Sign review</Button></div>
      </div>
    </Dialog>
  );
}

function RecaptureDialog({ open, onClose, onSubmit }: { open: boolean; onClose: () => void; onSubmit: (reason: string, eyes: string[]) => void }) {
  const [reason, setReason] = useState("");
  const [sel, setSel] = useState<Record<string, boolean>>({ right: true, left: true });
  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()} title="Request recapture" description="The technician will see your reason and upload new photographs.">
      <div className="space-y-4">
        <div className="flex gap-6"><Check label="Right eye (OD)" checked={sel.right} onChange={(x) => setSel({ ...sel, right: x })} /><Check label="Left eye (OS)" checked={sel.left} onChange={(x) => setSel({ ...sel, left: x })} /></div>
        <Field label="Reason"><Textarea value={reason} onChange={(e) => setReason(e.target.value)} placeholder="e.g. Macula not in field; eyelash artefact superiorly" /></Field>
        <div className="flex justify-end gap-2"><Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button variant="primary" disabled={reason.length < 3 || (!sel.right && !sel.left)} onClick={() => onSubmit(reason, Object.keys(sel).filter((k) => sel[k]))}>Send request</Button></div>
      </div>
    </Dialog>
  );
}
