"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Search } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { useFetch } from "@/lib/use-fetch";
import { fmtDate, STATUS_LABEL } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input, Select } from "@/components/ui/input";
import { Table, Td, Th } from "@/components/ui/table";
import { Empty, Loading, PageHeader, StatusBadge, SyntheticTag } from "@/components/app/bits";

export default function Screenings() {
  const { can } = useAuth();
  const router = useRouter();
  const [status, setStatus] = useState("");
  const [q, setQ] = useState("");
  const [dq, setDq] = useState("");
  useEffect(() => { const t = setTimeout(() => setDq(q), 300); return () => clearTimeout(t); }, [q]);
  const { data, loading } = useFetch<any>(`/screenings?page_size=100&q=${encodeURIComponent(dq)}${status ? `&status=${status}` : ""}`);
  return (
    <>
      <PageHeader title="Screenings" description="Every screening session, from image capture to signed report."
        actions={can("screenings.write") && <Button asChild variant="primary"><Link href="/app/screenings/new">New screening</Link></Button>} />
      <Card>
        <div className="flex flex-col gap-3 border-b border-line p-4 md:flex-row">
          <div className="relative flex-1"><Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate" />
            <Input className="pl-9" placeholder="Search by patient, patient ID or screening ID" value={q} onChange={(e) => setQ(e.target.value)} /></div>
          <Select className="md:w-56" value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">All statuses</option>{Object.entries(STATUS_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </Select>
        </div>
        {loading ? <Loading /> : !data?.items.length ? <Empty title="No screenings found" /> : (
          <Table>
            <thead><tr><Th>Patient</Th><Th>Screening ID</Th><Th>Started</Th><Th>Eyes</Th><Th>AI output</Th><Th>Status</Th></tr></thead>
            <tbody>{data.items.map((s: any) => (
              <tr key={s.id} className="cursor-pointer hover:bg-mist/60" onClick={() => router.push(`/app/screenings/${s.id}`)}>
                <Td><span className="font-medium text-navy">{s.patient_name}</span> {s.patient_is_synthetic && <SyntheticTag />}<div className="text-xs text-slate">{s.patient_code}</div></Td>
                <Td className="tabular text-slate">{s.screening_code}</Td>
                <Td className="text-slate">{fmtDate(s.created_at, true)}</Td>
                <Td className="text-slate">{s.eyes_uploaded.map((e: string) => (e === "right" ? "OD" : "OS")).join(" · ") || "—"}</Td>
                <Td className="max-w-[260px] text-xs">{Object.entries(s.ai_verdicts).map(([e, v]: any) => <div key={e} className="truncate"><span className="text-slate">{e === "right" ? "OD" : "OS"}:</span> {v}</div>)}{!Object.keys(s.ai_verdicts).length && <span className="text-slate">—</span>}</Td>
                <Td><StatusBadge status={s.status} /></Td>
              </tr>))}</tbody>
          </Table>
        )}
      </Card>
    </>
  );
}
