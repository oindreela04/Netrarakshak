"use client";
import { useEffect, useState } from "react";
import { useFetch } from "@/lib/use-fetch";
import { fmtDate } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Table, Td, Th } from "@/components/ui/table";
import { Loading, PageHeader } from "@/components/app/bits";

export default function Audit() {
  const [q, setQ] = useState("");
  const [dq, setDq] = useState("");
  const [page, setPage] = useState(1);
  useEffect(() => { const t = setTimeout(() => { setDq(q); setPage(1); }, 300); return () => clearTimeout(t); }, [q]);
  const { data, loading } = useFetch<any>(`/admin/audit?page=${page}&page_size=50&action=${encodeURIComponent(dq)}`);
  return (
    <>
      <PageHeader title="Audit log" description="Append-only and hash-chained. Each entry records who did what, when and from where." />
      <Card>
        <div className="border-b border-line p-4"><Input className="max-w-sm" placeholder="Filter by action, e.g. image.viewed, review.signed" value={q} onChange={(e) => setQ(e.target.value)} /></div>
        {loading ? <Loading /> : (
          <>
            <Table>
              <thead><tr><Th>Time (IST)</Th><Th>User</Th><Th>Action</Th><Th>Record</Th><Th>IP</Th><Th>Details</Th><Th>Hash</Th></tr></thead>
              <tbody>{data?.items.map((a: any) => (
                <tr key={a.id} className="align-top text-[13px]">
                  <Td className="whitespace-nowrap text-slate">{fmtDate(a.created_at, true)}</Td>
                  <Td>{a.user_email || <span className="text-slate">anonymous</span>}</Td>
                  <Td className="font-medium text-navy">{a.action}</Td>
                  <Td className="text-xs text-slate">{a.entity_type}{a.entity_id && <div className="font-mono">{a.entity_id.slice(0, 8)}</div>}</Td>
                  <Td className="text-xs text-slate">{a.ip_address}</Td>
                  <Td className="max-w-[280px] truncate font-mono text-[11px] text-slate" title={JSON.stringify(a.details)}>{Object.keys(a.details).length ? JSON.stringify(a.details) : ""}</Td>
                  <Td className="font-mono text-[11px] text-slate">{a.hash}</Td>
                </tr>))}</tbody>
            </Table>
            <div className="flex items-center justify-between px-4 py-3 text-sm text-slate">
              <span>{data?.total} entries</span>
              <div className="flex gap-2"><Button size="sm" variant="outline" disabled={page === 1} onClick={() => setPage(page - 1)}>Newer</Button><Button size="sm" variant="outline" disabled={page * 50 >= (data?.total ?? 0)} onClick={() => setPage(page + 1)}>Older</Button></div>
            </div>
          </>
        )}
      </Card>
    </>
  );
}
