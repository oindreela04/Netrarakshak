"use client";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";
import { Archive, ArchiveRestore, FileText, Pencil, Plus, Trash2 } from "lucide-react";
import { api } from "@/lib/api";
import { openReport } from "@/lib/reports";
import { useAuth } from "@/lib/auth";
import { useFetch } from "@/lib/use-fetch";
import { fmtDate, GRADE_LABEL } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { Field, Input, Select, Textarea } from "@/components/ui/input";
import { Table, Td, Th } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Empty, ErrorNote, Loading, PageHeader, StatusBadge, SyntheticTag } from "@/components/app/bits";
import { CONSENTS, fromPatient, PatientFields, toPayload } from "@/components/app/patient-form";

export default function PatientProfile() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { can } = useAuth();
  const { data: p, error, loading, reload } = useFetch<any>(`/patients/${id}`);
  const [edit, setEdit] = useState<any>(null);
  const [consentOpen, setConsentOpen] = useState(false);
  const [eraseOpen, setEraseOpen] = useState(false);

  if (loading && !p) return <Loading />;
  if (error) return <ErrorNote message={error} />;
  if (!p) return null;

  const act = async (fn: () => Promise<any>, ok: string) => { try { await fn(); toast.success(ok); reload(); } catch (e: any) { toast.error(e.message); } };
  

  return (
    <>
      <PageHeader
        title={p.full_name}
        description={<div className="flex flex-wrap items-center gap-2"><span className="tabular">{p.patient_code}</span><span>·</span><span>{p.age} years, {p.sex}</span>
          {p.has_diabetes && <Badge tone="blue">Diabetes</Badge>}{p.has_hypertension && <Badge tone="teal">Hypertension</Badge>}
          {p.is_synthetic && <SyntheticTag />}{p.is_archived && <Badge tone="warn">Archived</Badge>}</div>}
        actions={<>
          {can("patients.write") && !p.is_archived && <Button variant="outline" onClick={() => setEdit(fromPatient(p))}><Pencil />Edit</Button>}
          {can("patients.archive") && (p.is_archived
            ? <Button variant="outline" onClick={() => act(() => api(`/patients/${id}/restore`, { method: "POST" }), "Record restored")}><ArchiveRestore />Restore</Button>
            : <Button variant="outline" onClick={() => confirm("Archive this patient? The record is hidden from the directory but kept.") && act(() => api(`/patients/${id}/archive`, { method: "POST" }), "Record archived")}><Archive />Archive</Button>)}
          {can("hospital.manage") && p.is_archived && <Button variant="danger" onClick={() => setEraseOpen(true)}><Trash2 />Erase permanently</Button>}
          {can("screenings.write") && !p.is_archived && <Button asChild variant="primary"><Link href={`/app/screenings/new?patient=${id}`}><Plus />New screening</Link></Button>}
        </>}
      />
      {p.is_synthetic && <p className="mb-5 rounded-md border border-[#F4CFCB] bg-[#FCEDEC] px-4 py-2.5 text-sm text-danger">Synthetic test record — not a real person. Results for this record have no clinical meaning.</p>}
      {!p.consent_state.screening && <p className="mb-5 rounded-md border border-[#F0DDB8] bg-[#FBF2E3] px-4 py-2.5 text-sm text-warn">Screening consent is not recorded. Record consent before starting a screening.</p>}

      <Tabs defaultValue="history">
        <TabsList>
          <TabsTrigger value="history">Screening history ({p.screenings.length})</TabsTrigger>
          <TabsTrigger value="details">Clinical details</TabsTrigger>
          <TabsTrigger value="reports">Reports ({p.reports.length})</TabsTrigger>
          <TabsTrigger value="consent">Consent</TabsTrigger>
        </TabsList>

        <TabsContent value="history" className="pt-5">
          <Card>
            {!p.screenings.length ? <Empty title="No screenings yet" body="Start a screening to capture and analyse retinal photographs." /> : (
              <Table>
                <thead><tr><Th>Date</Th><Th>Screening</Th><Th>AI output</Th><Th>Clinician grade</Th><Th>Status</Th><Th /></tr></thead>
                <tbody>
                  {p.screenings.map((s: any) => (
                    <tr key={s.id} className="hover:bg-mist/60">
                      <Td className="text-slate">{fmtDate(s.created_at, true)}</Td>
                      <Td className="tabular">{s.screening_code}</Td>
                      <Td className="text-xs">{Object.entries(s.ai_verdicts).map(([e, v]: any) => <div key={e}><span className="text-slate">{e === "right" ? "OD" : "OS"}:</span> {v}</div>)}{!Object.keys(s.ai_verdicts).length && <span className="text-slate">Not run</span>}</Td>
                      <Td className="text-xs">{Object.entries(s.final_grades).map(([e, g]: any) => <div key={e}><span className="text-slate">{e === "right" ? "OD" : "OS"}:</span> <b>{GRADE_LABEL[g]}</b></div>)}{!Object.keys(s.final_grades).length && <span className="text-slate">Not signed</span>}</Td>
                      <Td><StatusBadge status={s.status} /></Td>
                      <Td className="text-right"><Button asChild size="sm" variant="outline"><Link href={`/app/screenings/${s.id}`}>Open</Link></Button></Td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            )}
          </Card>
        </TabsContent>

        <TabsContent value="details" className="pt-5">
          <div className="grid gap-6 lg:grid-cols-2">
            <Card><CardHeader title="Contact" /><CardBody><DL rows={[["Date of birth", fmtDate(p.date_of_birth)], ["Mobile", p.phone], ["Email", p.email], ["Address", p.address], ["Emergency contact", p.emergency_contact], ["ABHA ID", p.abha_id], ["Registered", fmtDate(p.created_at, true)]]} /></CardBody></Card>
            <Card><CardHeader title="Medical history" /><CardBody><DL rows={[
              ["Diabetes", p.has_diabetes ? [p.diabetes_type, p.diabetes_since_year && `since ${p.diabetes_since_year}`].filter(Boolean).join(", ") || "Yes" : "No"],
              ["Last HbA1c", p.last_hba1c ? `${p.last_hba1c}%` : ""],
              ["Hypertension", p.has_hypertension ? (p.hypertension_since_year ? `Since ${p.hypertension_since_year}` : "Yes") : "No"],
              ["Medications", p.medications], ["Other history", p.medical_history]]} /></CardBody></Card>
          </div>
        </TabsContent>

        <TabsContent value="reports" className="pt-5">
          <Card>
            {!p.reports.length ? <Empty title="No reports yet" /> : (
              <Table>
                <thead><tr><Th>Report</Th><Th>Generated</Th><Th>Status</Th><Th /></tr></thead>
                <tbody>{p.reports.map((r: any) => (
                  <tr key={r.id}><Td className="tabular">{r.report_number}</Td><Td className="text-slate">{fmtDate(r.generated_at, true)}</Td>
                    <Td><Badge tone={r.review_status === "CLINICIAN APPROVED" ? "ok" : "warn"}>{r.review_status}</Badge></Td>
                    <Td className="text-right"><Button size="sm" variant="outline" onClick={() => openReport(r.id, r.report_number)}><FileText />View PDF</Button></Td></tr>
                ))}</tbody>
              </Table>
            )}
          </Card>
        </TabsContent>

        <TabsContent value="consent" className="pt-5">
          <Card>
            <CardHeader title="Consent record" description="Every consent decision is kept. Withdrawal stops future AI analysis immediately."
              action={can("consent.write") && <Button size="sm" variant="outline" onClick={() => setConsentOpen(true)}>Record consent</Button>} />
            <div className="grid gap-px bg-line sm:grid-cols-4">
              {CONSENTS.map((c) => (
                <div key={c.key} className="bg-white p-4"><p className="text-[13px] text-slate">{c.label}</p>
                  <p className="mt-1">{p.consent_state[c.key] ? <Badge tone="ok">Granted</Badge> : <Badge tone="neutral">Not granted</Badge>}</p></div>
              ))}
            </div>
            <Table>
              <thead><tr><Th>Purpose</Th><Th>Decision</Th><Th>Method</Th><Th>Recorded</Th><Th>Withdrawn</Th><Th /></tr></thead>
              <tbody>{[...p.consents].reverse().map((c: any) => (
                <tr key={c.id}>
                  <Td>{CONSENTS.find((x) => x.key === c.consent_type)?.label}</Td>
                  <Td>{c.granted ? "Granted" : "Declined"}</Td><Td className="text-slate">{c.method.replace("_", " ")}</Td>
                  <Td className="text-slate">{fmtDate(c.recorded_at, true)}</Td><Td className="text-slate">{fmtDate(c.withdrawn_at, true)}</Td>
                  <Td className="text-right">{c.granted && !c.withdrawn_at && can("consent.write") &&
                    <Button size="sm" variant="ghost" onClick={() => confirm("Record withdrawal of this consent?") && act(() => api(`/patients/${id}/consents/${c.id}/withdraw`, { method: "POST" }), "Consent withdrawn")}>Withdraw</Button>}</Td>
                </tr>
              ))}</tbody>
            </Table>
          </Card>
        </TabsContent>
      </Tabs>

      <Dialog open={!!edit} onOpenChange={(o) => !o && setEdit(null)} title="Edit patient" wide>
        {edit && <form onSubmit={(e) => { e.preventDefault(); act(() => api(`/patients/${id}`, { method: "PUT", json: toPayload(edit) }), "Patient updated").then(() => setEdit(null)); }}>
          <PatientFields v={edit} set={setEdit} />
          <div className="mt-6 flex justify-end gap-2"><Button type="button" variant="outline" onClick={() => setEdit(null)}>Cancel</Button><Button type="submit" variant="primary">Save changes</Button></div>
        </form>}
      </Dialog>
      <ConsentDialog open={consentOpen} onClose={() => setConsentOpen(false)} onSaved={reload} pid={id} />
      <EraseDialog open={eraseOpen} onClose={() => setEraseOpen(false)} code={p.patient_code}
        onErase={async () => { try { await api(`/patients/${id}?confirm_code=${encodeURIComponent(p.patient_code)}`, { method: "DELETE" }); toast.success("Patient permanently erased"); router.push("/app/patients"); } catch (e: any) { toast.error(e.message); } }} />
    </>
  );
}

function DL({ rows }: { rows: [string, any][] }) {
  return <dl className="divide-y divide-line text-sm">{rows.map(([k, v]) => <div key={k} className="grid grid-cols-[150px_1fr] gap-3 py-2.5"><dt className="text-slate">{k}</dt><dd className="whitespace-pre-wrap text-ink">{v || "—"}</dd></div>)}</dl>;
}

function ConsentDialog({ open, onClose, onSaved, pid }: { open: boolean; onClose: () => void; onSaved: () => void; pid: string }) {
  const [f, setF] = useState({ consent_type: "screening", granted: "true", method: "written", notes: "" });
  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()} title="Record consent">
      <form className="space-y-4" onSubmit={async (e) => {
        e.preventDefault();
        try { await api(`/patients/${pid}/consents`, { method: "POST", json: { ...f, granted: f.granted === "true" } }); toast.success("Consent recorded"); onSaved(); onClose(); }
        catch (err: any) { toast.error(err.message); }
      }}>
        <Field label="Purpose"><Select value={f.consent_type} onChange={(e) => setF({ ...f, consent_type: e.target.value })}>{CONSENTS.map((c) => <option key={c.key} value={c.key}>{c.label}</option>)}</Select></Field>
        <Field label="Decision"><Select value={f.granted} onChange={(e) => setF({ ...f, granted: e.target.value })}><option value="true">Granted</option><option value="false">Declined</option></Select></Field>
        <Field label="Method"><Select value={f.method} onChange={(e) => setF({ ...f, method: e.target.value })}><option value="written">Signed form</option><option value="digital">Digital signature</option><option value="verbal_witnessed">Verbal, witnessed</option></Select></Field>
        <Field label="Notes"><Textarea value={f.notes} onChange={(e) => setF({ ...f, notes: e.target.value })} placeholder="Form reference, witness name, language…" /></Field>
        <div className="flex justify-end gap-2"><Button type="button" variant="outline" onClick={onClose}>Cancel</Button><Button type="submit" variant="primary">Record consent</Button></div>
      </form>
    </Dialog>
  );
}

function EraseDialog({ open, onClose, code, onErase }: { open: boolean; onClose: () => void; code: string; onErase: () => void }) {
  const [typed, setTyped] = useState("");
  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()} title="Erase patient permanently"
      description="All screenings, images, AI results, reviews and reports for this patient will be securely deleted. This cannot be undone. The erasure is recorded in the audit log.">
      <Field label={`Type ${code} to confirm`}><Input value={typed} onChange={(e) => setTyped(e.target.value)} /></Field>
      <div className="mt-5 flex justify-end gap-2"><Button variant="outline" onClick={onClose}>Cancel</Button><Button variant="danger" disabled={typed !== code} onClick={onErase}>Erase permanently</Button></div>
    </Dialog>
  );
}
