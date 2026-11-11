"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Plus, Search } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { useFetch } from "@/lib/use-fetch";
import { fmtDate } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input, Select } from "@/components/ui/input";
import { Table, Td, Th } from "@/components/ui/table";
import { Empty, ErrorNote, Loading, PageHeader, StatusBadge, SyntheticTag } from "@/components/app/bits";

export default function Patients() {
  const { can } = useAuth();
  const router = useRouter();
  const [q, setQ] = useState("");
  const [dq, setDq] = useState("");
  const [cond, setCond] = useState("");
  const [archived, setArchived] = useState(false);
  const [page, setPage] = useState(1);
  useEffect(() => { const t = setTimeout(() => { setDq(q); setPage(1); }, 300); return () => clearTimeout(t); }, [q]);
  const params = new URLSearchParams({ q: dq, page: String(page), page_size: "25", archived: String(archived) });
  if (cond === "diabetes") params.set("diabetes", "true");
  if (cond === "hypertension") params.set("hypertension", "true");
  const { data, error, loading } = useFetch<any>(`/patients?${params}`);

  return (
    <>
      <PageHeader title="Patients" description={data ? `${data.total} ${archived ? "archived" : "active"} patient records` : undefined}
        actions={can("patients.write") && <Button asChild variant="primary"><Link href="/app/patients/new"><Plus />Register patient</Link></Button>} />
      <Card>
        <div className="flex flex-col gap-3 border-b border-line p-4 md:flex-row">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate" />
            <Input className="pl-9" placeholder="Search by name, patient ID or mobile number" value={q} onChange={(e) => setQ(e.target.value)} />
          </div>
          <Select className="md:w-48" value={cond} onChange={(e) => { setCond(e.target.value); setPage(1); }}>
            <option value="">All conditions</option><option value="diabetes">Diabetes</option><option value="hypertension">Hypertension</option>
          </Select>
          <Select className="md:w-40" value={String(archived)} onChange={(e) => { setArchived(e.target.value === "true"); setPage(1); }}>
            <option value="false">Active</option><option value="true">Archived</option>
          </Select>
        </div>
        {error && <div className="p-4"><ErrorNote message={error} /></div>}
        {loading ? <Loading /> : !data?.items.length ? (
          <Empty title={dq ? "No patients match your search" : "No patients registered yet"} body={dq ? "Check the spelling or search by patient ID." : "Register the first patient to start screening."}
            action={can("patients.write") && !dq && <Button asChild variant="primary"><Link href="/app/patients/new">Register patient</Link></Button>} />
        ) : (
          <>
            <Table>
              <thead><tr><Th>Patient</Th><Th>Patient ID</Th><Th>Age / sex</Th><Th>Conditions</Th><Th>Screenings</Th><Th>Last screening</Th></tr></thead>
              <tbody>
                {data.items.map((p: any) => (
                  <tr key={p.id} className="cursor-pointer hover:bg-mist/60" onClick={() => router.push(`/app/patients/${p.id}`)}>
                    <Td><span className="font-medium text-navy">{p.full_name}</span> {p.is_synthetic && <SyntheticTag />}<div className="text-xs text-slate">{p.phone || "No phone"}</div></Td>
                    <Td className="tabular text-slate">{p.patient_code}</Td>
                    <Td className="text-slate">{p.age} · {p.sex === "unspecified" ? "—" : p.sex[0].toUpperCase()}</Td>
                    <Td className="space-x-1">{p.has_diabetes && <Badge tone="blue">Diabetes</Badge>}{p.has_hypertension && <Badge tone="teal">Hypertension</Badge>}{!p.has_diabetes && !p.has_hypertension && <span className="text-slate">—</span>}</Td>
                    <Td className="tabular">{p.screening_count}</Td>
                    <Td>{p.last_screening_at ? <div className="flex items-center gap-2"><span className="text-slate">{fmtDate(p.last_screening_at)}</span><StatusBadge status={p.last_screening_status} /></div> : <span className="text-slate">Never</span>}</Td>
                  </tr>
                ))}
              </tbody>
            </Table>
            <div className="flex items-center justify-between px-4 py-3 text-sm text-slate">
              <span>Page {page} of {Math.max(1, Math.ceil(data.total / 25))}</span>
              <div className="flex gap-2">
                <Button size="sm" variant="outline" disabled={page === 1} onClick={() => setPage(page - 1)}>Previous</Button>
                <Button size="sm" variant="outline" disabled={page * 25 >= data.total} onClick={() => setPage(page + 1)}>Next</Button>
              </div>
            </div>
          </>
        )}
      </Card>
    </>
  );
}
