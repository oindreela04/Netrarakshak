"use client";
import { useState } from "react";
import { useFetch } from "@/lib/use-fetch";
import { GRADE_LABEL, STATUS_LABEL } from "@/lib/utils";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { Select } from "@/components/ui/input";
import { Loading, PageHeader, Stat } from "@/components/app/bits";
import { HBars, VolumeChart } from "@/components/app/charts";

const toBars = (o: Record<string, number>, labels: Record<string, string>, order?: string[]) =>
  (order ?? Object.keys(o)).map((k) => ({ name: labels[k] ?? k, value: o[k] ?? 0 }));

export default function Analytics() {
  const [days, setDays] = useState(90);
  const { data: d, loading } = useFetch<any>(`/analytics/dashboard?days=${days}`);
  return (
    <>
      <PageHeader title="Analytics" description="Computed from recorded screenings, AI results and signed reviews."
        actions={<Select className="w-40" value={days} onChange={(e) => setDays(Number(e.target.value))}><option value={30}>Last 30 days</option><option value={90}>Last 90 days</option><option value={365}>Last 12 months</option></Select>} />
      {loading || !d ? <Loading /> : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <Stat label="Screenings" value={d.totals.screenings} />
            <Stat label="Recapture rate" value={(() => { const t = Object.values(d.image_quality as Record<string, number>).reduce((a, b) => a + b, 0); return t ? `${Math.round(((d.image_quality.recapture_required ?? 0) / t) * 100)}%` : "—"; })()} sub="Images failing the quality check" />
            <Stat label="Referrals recommended" value={d.totals.referrals} />
            <Stat label="AI marked inconclusive" value={d.ai_uncertain} sub="Model below certainty thresholds" />
          </div>
          <div className="mt-6 grid gap-6 lg:grid-cols-2">
            <Card className="lg:col-span-2"><CardHeader title="Screening volume" /><CardBody><VolumeChart data={d.daily} /></CardBody></Card>
            <Card><CardHeader title="Pipeline status" /><CardBody><HBars data={toBars(d.status_counts, STATUS_LABEL, Object.keys(STATUS_LABEL))} colors={["#1F6FB2"]} /></CardBody></Card>
            <Card><CardHeader title="Image quality" description="All uploaded photographs" /><CardBody>
              <HBars data={toBars(d.image_quality, { acceptable: "Acceptable", inconclusive: "Inconclusive", recapture_required: "Recapture required" }, ["acceptable", "inconclusive", "recapture_required"])} colors={["#2E7D5B", "#B26B00", "#B42318"]} /></CardBody></Card>
            <Card><CardHeader title="AI step outcome" description="Per eye" /><CardBody>
              <HBars data={toBars(d.ai_status, { completed: "Completed", model_unavailable: "No active model", quality_rejected: "Skipped: quality", consent_missing: "Skipped: no consent", error: "Error" })} colors={["#3E8E8A"]} /></CardBody></Card>
            <Card><CardHeader title="Clinician decision on AI output" description="From signed reviews, per eye" /><CardBody>
              <HBars data={toBars(d.ai_decisions, { accept: "Accepted", modify: "Modified", reject: "Rejected", not_applicable: "No AI finding" }, ["accept", "modify", "reject", "not_applicable"])} colors={["#2E7D5B", "#1F6FB2", "#B42318", "#94A3B8"]} /></CardBody></Card>
            <Card className="lg:col-span-2"><CardHeader title="Clinician final grades" description="From signed reviews, per eye" /><CardBody>
              <HBars data={toBars(d.clinician_grades, GRADE_LABEL, Object.keys(GRADE_LABEL))} colors={["#2E7D5B", "#3E8E8A", "#1F6FB2", "#B26B00", "#B42318", "#5B6B7F", "#94A3B8"]} /></CardBody></Card>
          </div>
          <p className="mt-6 text-xs text-slate">Operational statistics only. Agreement between clinicians and the AI in routine use is not a clinical validation of the AI.</p>
        </>
      )}
    </>
  );
}
