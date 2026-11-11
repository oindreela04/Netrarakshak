"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { Download, FileText, Printer, Search } from "lucide-react";
import { openReport } from "@/lib/reports";
import { useFetch } from "@/lib/use-fetch";
import { fmtDate } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Table, Td, Th } from "@/components/ui/table";
import { Empty, Loading, PageHeader, SyntheticTag } from "@/components/app/bits";

export default function Reports() {
  const [q, setQ] = useState("");
  const [dq, setDq] = useState("");
  useEffect(() => { const t = setTimeout(() => setDq(q), 300); return () => clearTimeout(t); }, [q]);
  const { data, loading } = useFetch<any>(`/reports?page_size=100&q=${encodeURIComponent(dq)}`);
  return (
    <>
      <PageHeader title="Screening reports" description="Every generated report is kept. Only reports issued after a clinician's signature are marked approved." />
      <Card>
        <div className="border-b border-line p-4"><div className="relative max-w-md"><Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate" />
          <Input className="pl-9" placeholder="Search by report number, patient or patient ID" value={q} onChange={(e) => setQ(e.target.value)} /></div></div>
        {loading ? <Loading /> : !data?.items.length ? <Empty title="No reports found" /> : (
          <Table>
            <thead><tr><Th>Report</Th><Th>Patient</Th><Th>Generated</Th><Th>Review status</Th><Th /></tr></thead>
            <tbody>{data.items.map((r: any) => (
              <tr key={r.id}>
                <Td className="tabular">{r.report_number}</Td>
                <Td><Link className="font-medium text-navy hover:underline" href={`/app/patients/${r.patient_id}`}>{r.patient_name}</Link> {r.patient_is_synthetic && <SyntheticTag />}<div className="text-xs text-slate">{r.patient_code}</div></Td>
                <Td className="text-slate">{fmtDate(r.generated_at, true)}</Td>
                <Td><Badge tone={r.review_status === "CLINICIAN APPROVED" ? "ok" : "warn"}>{r.review_status}</Badge></Td>
                <Td className="whitespace-nowrap text-right">
                  <Button size="icon" variant="ghost" title="View" onClick={() => openReport(r.id, r.report_number)}><FileText /></Button>
                  <Button size="icon" variant="ghost" title="Print" onClick={() => openReport(r.id, r.report_number, "print")}><Printer /></Button>
                  <Button size="icon" variant="ghost" title="Download" onClick={() => openReport(r.id, r.report_number, "download")}><Download /></Button>
                </Td>
              </tr>))}</tbody>
          </Table>
        )}
      </Card>
    </>
  );
}
