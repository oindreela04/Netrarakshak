"use client";
import { useRouter } from "next/navigation";
import { useFetch } from "@/lib/use-fetch";
import { fmtDate } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Table, Td, Th } from "@/components/ui/table";
import { Empty, Loading, PageHeader, StatusBadge, SyntheticTag } from "@/components/app/bits";

export default function ReviewQueue() {
  const router = useRouter();
  const { data, loading } = useFetch<any[]>("/reviews/queue");
  return (
    <>
      <PageHeader title="Review queue" description="Cases with an AI-suggested referable grade come first, then cases the AI could not resolve, then the rest by age." />
      <Card>
        {loading ? <Loading /> : !data?.length ? <Empty title="Nothing waiting for review" body="New screenings appear here once images are uploaded." /> : (
          <Table>
            <thead><tr><Th>Patient</Th><Th>Waiting since</Th><Th>AI output</Th><Th>Priority</Th><Th>Status</Th></tr></thead>
            <tbody>{data.map((s) => (
              <tr key={s.id} className="cursor-pointer hover:bg-mist/60" onClick={() => router.push(`/app/review/${s.id}`)}>
                <Td><span className="font-medium text-navy">{s.patient_name}</span> {s.patient_is_synthetic && <SyntheticTag />}
                  <div className="text-xs text-slate">{s.patient_code} · {s.patient_age} y{s.has_diabetes ? " · diabetes" : ""}</div></Td>
                <Td className="text-slate">{fmtDate(s.created_at, true)}</Td>
                <Td className="max-w-[300px] text-xs">{Object.entries(s.ai_verdicts).map(([e, v]: any) => <div key={e} className="truncate"><span className="text-slate">{e === "right" ? "OD" : "OS"}:</span> {v}</div>)}{!Object.keys(s.ai_verdicts).length && <span className="text-slate">AI not run</span>}</Td>
                <Td>{s.referable_suggested ? <Badge tone="danger">Referable suggested</Badge> : s.needs_attention ? <Badge tone="warn">Needs human judgement</Badge> : <Badge>Routine</Badge>}</Td>
                <Td><StatusBadge status={s.status} /></Td>
              </tr>))}</tbody>
          </Table>
        )}
      </Card>
    </>
  );
}
