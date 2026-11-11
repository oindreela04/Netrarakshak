"use client";
import Link from "next/link";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Plus, Stethoscope } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { useFetch } from "@/lib/use-fetch";
import { fmtDate } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { Table, Td, Th } from "@/components/ui/table";
import { Empty, ErrorNote, Loading, PageHeader, Stat, StatusBadge, SyntheticTag } from "@/components/app/bits";
import { HBars, VolumeChart } from "@/components/app/charts";

export default function Dashboard() {
  const { me, can } = useAuth();
  const router = useRouter();
  useEffect(() => { if (me && !me.hospital) router.replace("/app/platform"); }, [me, router]);
  const { data, error, loading } = useFetch<any>(me?.hospital ? "/analytics/dashboard?days=30" : null);
  const recent = useFetch<any>(me?.hospital ? "/screenings?page_size=8" : null);
  if (!me?.hospital) return <Loading />;

  const t = data?.totals;
  return (
    <>
      <PageHeader
        title={`Good ${new Date().getHours() < 12 ? "morning" : new Date().getHours() < 17 ? "afternoon" : "evening"}`}
        description={`${me.user.full_name} · ${me.hospital.name} · last 30 days`}
        actions={<>
          {can("patients.write") && <Button asChild variant="outline"><Link href="/app/patients/new"><Plus />Register patient</Link></Button>}
          {can("screenings.write") && <Button asChild variant="primary"><Link href="/app/screenings/new">New screening</Link></Button>}
          {can("review.write") && <Button asChild variant="teal"><Link href="/app/review"><Stethoscope />Review queue</Link></Button>}
        </>}
      />
      {error && <ErrorNote message={error} />}
      {loading || !t ? <Loading /> : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
            <Stat label="Active patients" value={t.patients} sub={`${t.diabetic_patients} with diabetes`} />
            <Stat label="Screenings" value={t.screenings} sub="Last 30 days" />
            <Stat label="Awaiting review" value={t.awaiting_review} sub={t.recapture_requested ? `${t.recapture_requested} need recapture` : "No recaptures pending"} />
            <Stat label="Signed by clinician" value={t.signed} sub={`${t.referrals} referral${t.referrals === 1 ? "" : "s"} recommended`} />
            <Stat label="Median sign-off time" value={t.median_turnaround_hours != null ? `${t.median_turnaround_hours} h` : "—"} sub="Capture to signature" />
          </div>
          <div className="mt-6 grid gap-6 xl:grid-cols-[1.6fr_1fr]">
            <Card><CardHeader title="Screening volume" description="Sessions started per day" /><CardBody><VolumeChart data={data.daily.slice(-30)} /></CardBody></Card>
            <Card><CardHeader title="Clinician final grades" description="From signed reviews, per eye" /><CardBody>
              <HBars colors={["#2E7D5B", "#3E8E8A", "#1F6FB2", "#B26B00", "#B42318", "#5B6B7F", "#94A3B8"]}
                data={["no_dr", "mild_npdr", "moderate_npdr", "severe_npdr", "proliferative_dr", "ungradable"].map((k) => ({
                  name: ({ no_dr: "No apparent DR", mild_npdr: "Mild NPDR", moderate_npdr: "Moderate NPDR", severe_npdr: "Severe NPDR", proliferative_dr: "Proliferative DR", ungradable: "Ungradable" } as any)[k],
                  value: data.clinician_grades[k] ?? 0 }))} />
            </CardBody></Card>
          </div>
        </>
      )}
      <Card className="mt-6">
        <CardHeader title="Recent screenings" action={<Button asChild variant="link" size="sm"><Link href="/app/screenings">View all</Link></Button>} />
        {recent.loading ? <Loading /> : !recent.data?.items.length ? (
          <Empty title="No screenings yet" body="Register a patient and start a screening session to see it here." />
        ) : (
          <Table>
            <thead><tr><Th>Patient</Th><Th>Screening</Th><Th>Started</Th><Th>Eyes</Th><Th>Status</Th></tr></thead>
            <tbody>
              {recent.data.items.map((s: any) => (
                <tr key={s.id} className="cursor-pointer hover:bg-mist/60" onClick={() => router.push(`/app/screenings/${s.id}`)}>
                  <Td><span className="font-medium text-navy">{s.patient_name}</span> {s.patient_is_synthetic && <SyntheticTag />}<div className="text-xs text-slate">{s.patient_code}</div></Td>
                  <Td className="tabular text-slate">{s.screening_code}</Td>
                  <Td className="text-slate">{fmtDate(s.created_at, true)}</Td>
                  <Td className="text-slate">{s.eyes_uploaded.length ? s.eyes_uploaded.map((e: string) => (e === "right" ? "OD" : "OS")).join(" · ") : "—"}</Td>
                  <Td><StatusBadge status={s.status} /></Td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </Card>
    </>
  );
}
