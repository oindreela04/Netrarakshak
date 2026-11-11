"use client";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";
import { Brain, Download, FileText, Printer, Stethoscope } from "lucide-react";
import { api } from "@/lib/api";
import { openReport } from "@/lib/reports";
import { useAuth } from "@/lib/auth";
import { useFetch } from "@/lib/use-fetch";
import { cn, fmtDate, GRADE_LABEL } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { Table, Td, Th } from "@/components/ui/table";
import { ErrorNote, Loading, PageHeader, QualityBadge, StatusBadge, SyntheticTag } from "@/components/app/bits";
import { RetinalViewer } from "@/components/app/retinal-viewer";
import { AIResultCard, EyeDrop, QualityChecks } from "@/components/app/screening-parts";

const STEPS = ["Images", "Quality", "AI analysis", "Clinician review", "Report"];

export default function ScreeningDetail() {
  const { id } = useParams<{ id: string }>();
  const { can } = useAuth();
  const { data: s, error, loading, reload } = useFetch<any>(`/screenings/${id}`);
  const modules = useFetch<any[]>("/ai/modules");
  const [uploading, setUploading] = useState<string | null>(null);
  const [analysing, setAnalysing] = useState(false);
  const [generating, setGenerating] = useState(false);

  if (loading && !s) return <Loading />;
  if (error) return <ErrorNote message={error} />;
  if (!s) return null;

  const img = (eye: string) => s.images.find((i: any) => i.eye === eye);
  const ai = (eye: string) => s.ai_results.find((r: any) => r.eye === eye);
  const locked = ["signed", "reported"].includes(s.status);
  const signed = [...s.reviews].reverse().find((r: any) => r.status === "signed");
  const dr = modules.data?.find((m) => m.key === "diabetic_retinopathy");

  const step = s.reports.some((r: any) => r.review_status === "CLINICIAN APPROVED") ? 5 : signed ? 4 : s.ai_results.length ? 3 : s.images.length ? 2 : 0;

  async function upload(eye: string, f: File) {
    setUploading(eye);
    const fd = new FormData(); fd.append("file", f); fd.append("source", "manual_upload");
    try {
      const r = await api<any>(`/screenings/${id}/images/${eye}`, { method: "POST", body: fd });
      r.quality_verdict === "acceptable" ? toast.success(`${eye === "right" ? "Right" : "Left"} eye: image quality acceptable`)
        : toast.warning(`${eye === "right" ? "Right" : "Left"} eye: ${r.quality.summary}`);
      reload();
    } catch (e: any) { toast.error(e.message); } finally { setUploading(null); }
  }
  async function analyse() {
    setAnalysing(true);
    try { await api(`/screenings/${id}/analyse`, { method: "POST" }); toast.success("AI screening step complete"); reload(); }
    catch (e: any) { toast.error(e.message); } finally { setAnalysing(false); }
  }
  async function generate() {
    setGenerating(true);
    try { const r = await api<any>(`/reports/screening/${id}`, { method: "POST" }); toast.success(`Report ${r.report_number} generated`); reload(); openReport(r.id, r.report_number); }
    catch (e: any) { toast.error(e.message); } finally { setGenerating(false); }
  }
  const openPdf = (rid: string, mode: "view" | "print" | "download" = "view") => openReport(rid, s.reports.find((r: any) => r.id === rid)?.report_number ?? rid, mode);

  const eyeView = (eye: "right" | "left") => {
    const i = img(eye), r = ai(eye);
    return {
      label: eye === "right" ? "Right eye (OD)" : "Left eye (OS)",
      imagePath: i ? `/screenings/${id}/images/${i.id}/file` : undefined,
      overlayPath: r?.has_gradcam ? `/screenings/${id}/ai/${r.id}/overlay` : undefined,
      heatmapPath: r?.has_gradcam ? `/screenings/${id}/ai/${r.id}/heatmap` : undefined,
      quality: i?.quality_verdict, qualitySummary: i?.quality?.summary,
    };
  };

  return (
    <>
      <PageHeader
        title={s.patient.full_name}
        description={<div className="flex flex-wrap items-center gap-2"><Link className="text-clinical hover:underline" href={`/app/patients/${s.patient.id}`}>{s.patient.patient_code}</Link>
          <span>·</span><span className="tabular">{s.screening_code}</span><span>·</span><span>{fmtDate(s.created_at, true)}</span><StatusBadge status={s.status} />{s.patient.is_synthetic && <SyntheticTag />}</div>}
        actions={<>
          {can("review.write") && !locked && s.images.length > 0 && <Button asChild variant="teal"><Link href={`/app/review/${id}`}><Stethoscope />Open in review workspace</Link></Button>}
          {can("reports.generate") && s.images.length > 0 && <Button variant="primary" disabled={generating} onClick={generate}><FileText />{generating ? "Generating…" : signed ? "Generate signed report" : "Generate draft report"}</Button>}
        </>}
      />

      <ol className="mb-6 grid grid-cols-5 overflow-hidden rounded-lg border border-line bg-white text-[12.5px]">
        {STEPS.map((t, i) => (
          <li key={t} className={cn("flex items-center gap-2 border-r border-line px-3 py-2.5 last:border-0", i < step ? "text-teal-700" : i === step ? "font-semibold text-navy" : "text-slate")}>
            <span className={cn("flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[11px]", i < step ? "bg-teal text-white" : i === step ? "bg-navy text-white" : "bg-mist")}>{i + 1}</span>
            <span className="hidden truncate sm:inline">{t}</span>
          </li>
        ))}
      </ol>

      {s.status === "recapture_requested" && (
        <p className="mb-5 rounded-md border border-[#F4CFCB] bg-[#FCEDEC] px-4 py-3 text-sm text-danger">
          Recapture requested by the reviewing ophthalmologist: {[...s.reviews].reverse().find((r: any) => r.recapture_requested)?.recapture_reason}. Upload new photographs below, then run AI screening again.
        </p>
      )}

      <div className="grid gap-6 xl:grid-cols-[1fr_380px]">
        <div className="space-y-6">
          <div className="grid gap-4 md:grid-cols-2">
            {(["right", "left"] as const).map((eye) => (
              <EyeDrop key={eye} eye={eye} image={img(eye)} screeningId={id} disabled={locked || !can("screenings.write")} busy={uploading === eye} onFile={(f) => upload(eye, f)} />
            ))}
          </div>
          {s.images.length > 0 && <RetinalViewer right={eyeView("right")} left={eyeView("left")} />}
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader title="AI screening" description="Diabetic retinopathy module"
              action={can("ai.run") && !locked && <Button size="sm" variant="primary" disabled={analysing || !s.images.length} onClick={analyse}><Brain />{analysing ? "Analysing…" : s.ai_results.length ? "Run again" : "Run AI screening"}</Button>} />
            <CardBody className="space-y-3">
              {dr && !dr.available && <p className="rounded-md bg-[#FBF2E3] px-3 py-2 text-xs leading-5 text-warn"><b>No active AI model.</b> {dr.reason} Screenings are still completed by clinician review.</p>}
              {dr?.available && <p className="rounded-md bg-clinical-50 px-3 py-2 text-xs leading-5 text-clinical-600">Model {dr.version}: {dr.card?.clinical_use_status}</p>}
              {!s.patient_consents?.ai_analysis && <p className="rounded-md bg-mist px-3 py-2 text-xs text-slate">Patient has not consented to AI analysis; no AI processing will run.</p>}
              <AIResultCard eye="right" r={ai("right")} />
              <AIResultCard eye="left" r={ai("left")} />
              <p className="text-[11px] leading-4 text-slate">Images that fail the quality check are never analysed. Only diabetic retinopathy is assessed; other conditions are not excluded.</p>
            </CardBody>
          </Card>

          {s.images.length > 0 && (
            <Card>
              <CardHeader title="Image quality" description="Checked automatically before any AI analysis" />
              <CardBody className="space-y-2 py-3">
                {[...s.images].sort((a: any, b: any) => (a.eye === "right" ? -1 : 1)).map((i: any) => (
                  <details key={i.id} open={i.quality_verdict !== "acceptable"} className="group rounded-md border border-line">
                    <summary className="flex cursor-pointer items-center justify-between gap-3 px-3 py-2.5 text-sm font-medium text-navy">
                      <span>{i.eye === "right" ? "Right eye (OD)" : "Left eye (OS)"}</span><QualityBadge verdict={i.quality_verdict} />
                    </summary>
                    <div className="border-t border-line px-3 py-1"><p className="py-2 text-xs text-slate">{i.quality?.summary}</p><QualityChecks quality={i.quality} /></div>
                  </details>
                ))}
              </CardBody>
            </Card>
          )}
        </div>
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader title="Clinician interpretation" description={signed ? `Signed by ${signed.reviewer_name} · ${fmtDate(signed.signed_at, true)}` : "Not yet signed"} />
          <CardBody>
            {signed ? (
              <div className="space-y-3 text-sm">
                {(["right", "left"] as const).map((e) => signed.eye_findings[e] && (
                  <div key={e} className="flex items-start justify-between gap-4 border-b border-line pb-2">
                    <span className="text-slate">{e === "right" ? "Right eye (OD)" : "Left eye (OS)"}</span>
                    <span className="text-right"><b className="text-navy">{GRADE_LABEL[signed.eye_findings[e].final_grade]}</b><span className="block text-xs text-slate">{signed.eye_findings[e].ai_decision.replace("_", " ")} AI suggestion</span></span>
                  </div>
                ))}
                {signed.overall_impression && <p><span className="text-slate">Impression: </span>{signed.overall_impression}</p>}
                <p><span className="text-slate">Recommendations: </span>{signed.recommendations || "—"}</p>
                {signed.referral_recommended && <Badge tone="danger">Referral recommended · {signed.referral_urgency || "routine"}</Badge>}
              </div>
            ) : <p className="text-sm text-slate">An ophthalmologist must review and sign this screening before an approved report can be issued.</p>}
          </CardBody>
        </Card>
        <Card>
          <CardHeader title="Reports" />
          {!s.reports.length ? <CardBody><p className="text-sm text-slate">No reports generated.</p></CardBody> : (
            <Table>
              <thead><tr><Th>Report</Th><Th>Status</Th><Th /></tr></thead>
              <tbody>{[...s.reports].reverse().map((r: any) => (
                <tr key={r.id}>
                  <Td><span className="tabular">{r.report_number}</span><div className="text-xs text-slate">{fmtDate(r.generated_at, true)}</div></Td>
                  <Td><Badge tone={r.review_status === "CLINICIAN APPROVED" ? "ok" : "warn"}>{r.review_status}</Badge></Td>
                  <Td className="whitespace-nowrap text-right">
                    <Button size="icon" variant="ghost" title="View" onClick={() => openPdf(r.id)}><FileText /></Button>
                    <Button size="icon" variant="ghost" title="Print" onClick={() => openPdf(r.id, "print")}><Printer /></Button>
                    <Button size="icon" variant="ghost" title="Download" onClick={() => openPdf(r.id, "download")}><Download /></Button>
                  </Td>
                </tr>))}</tbody>
            </Table>
          )}
        </Card>
      </div>
    </>
  );
}
