"use client";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { Plus, Upload } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useFetch } from "@/lib/use-fetch";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { Check, Field, Input } from "@/components/ui/input";
import { Table, Td, Th } from "@/components/ui/table";
import { Loading, PageHeader, SecureImage } from "@/components/app/bits";

export default function HospitalPage() {
  const { reload: reloadMe } = useAuth();
  const { data, loading, reload } = useFetch<any>("/admin/hospital");
  const [f, setF] = useState<any>(null);
  const [branch, setBranch] = useState<any>(null);
  const [logoV, setLogoV] = useState(0);
  const file = useRef<HTMLInputElement>(null);
  useEffect(() => { if (data) setF({ name: data.name, email: data.email, phone: data.phone, address: data.address, city: data.city, state: data.state, gstin: data.gstin, brand_color: data.brand_color, report_header: data.report_header, report_footer: data.report_footer, retention_days: data.retention_days }); }, [data]);
  if (loading || !f) return <Loading />;
  const set = (k: string) => (e: any) => setF({ ...f, [k]: e.target.value });

  return (
    <>
      <PageHeader title="Hospital" description={`${data.code} · licence ${data.licence_key}`} />
      <div className="grid gap-6 xl:grid-cols-[1.4fr_1fr]">
        <form onSubmit={async (e) => { e.preventDefault(); try { await api("/admin/hospital", { method: "PUT", json: { ...f, retention_days: Number(f.retention_days) } }); toast.success("Hospital details saved"); reload(); reloadMe(); } catch (err: any) { toast.error(err.message); } }}>
          <Card>
            <CardHeader title="Profile and report branding" description="Shown in the report header and footer." action={<Button type="submit" size="sm" variant="primary">Save</Button>} />
            <CardBody className="grid gap-4 sm:grid-cols-2">
              <Field label="Hospital name" className="sm:col-span-2"><Input required value={f.name} onChange={set("name")} /></Field>
              <Field label="Email"><Input value={f.email} onChange={set("email")} /></Field>
              <Field label="Phone"><Input value={f.phone} onChange={set("phone")} /></Field>
              <Field label="Address" className="sm:col-span-2"><Input value={f.address} onChange={set("address")} /></Field>
              <Field label="City"><Input value={f.city} onChange={set("city")} /></Field>
              <Field label="State"><Input value={f.state} onChange={set("state")} /></Field>
              <Field label="GSTIN"><Input value={f.gstin} onChange={set("gstin")} /></Field>
              <Field label="Brand colour" hint="Report header band"><div className="flex gap-2"><input type="color" value={f.brand_color} onChange={set("brand_color")} className="h-10 w-12 rounded border border-line" /><Input value={f.brand_color} onChange={set("brand_color")} /></div></Field>
              <Field label="Report header line" className="sm:col-span-2" hint="Defaults to the address"><Input value={f.report_header} onChange={set("report_header")} /></Field>
              <Field label="Report footer" className="sm:col-span-2"><Input value={f.report_footer} onChange={set("report_footer")} placeholder="e.g. NABH accredited · 24×7 emergency +91 …" /></Field>
              <Field label="Record retention (days)" hint="Archived records older than this are eligible for secure erasure. Follow your hospital's medical-records policy."><Input type="number" min={365} value={f.retention_days} onChange={set("retention_days")} /></Field>
            </CardBody>
          </Card>
        </form>
        <div className="space-y-6">
          <Card>
            <CardHeader title="Logo" description="PNG or JPEG, under 2 MB" action={<Button size="sm" variant="outline" onClick={() => file.current?.click()}><Upload />Upload</Button>} />
            <CardBody>
              <input ref={file} type="file" hidden accept="image/png,image/jpeg" onChange={async (e) => {
                const fl = e.target.files?.[0]; if (!fl) return;
                const fd = new FormData(); fd.append("file", fl);
                try { await api("/admin/hospital/logo", { method: "POST", body: fd }); toast.success("Logo updated"); setLogoV(logoV + 1); reload(); } catch (err: any) { toast.error(err.message); }
              }} />
              <div className="flex h-28 items-center justify-center rounded-md p-4" style={{ background: f.brand_color }}>
                {data.has_logo ? <SecureImage key={logoV} path={`/admin/hospital/logo?v=${logoV}`} alt="Hospital logo" className="max-h-20 object-contain" /> : <span className="text-sm text-white/70">No logo uploaded</span>}
              </div>
            </CardBody>
          </Card>
          <Card>
            <CardHeader title="Branches" action={<Button size="sm" variant="outline" onClick={() => setBranch({ name: "", city: "", address: "", is_active: true })}><Plus />Add branch</Button>} />
            <Table><tbody>{data.branches.map((b: any) => (
              <tr key={b.id}><Td><span className="font-medium text-navy">{b.name}</span><div className="text-xs text-slate">{b.city}</div></Td>
                <Td>{b.is_active ? <Badge tone="ok">Active</Badge> : <Badge>Inactive</Badge>}</Td>
                <Td className="text-right"><Button size="sm" variant="ghost" onClick={() => setBranch(b)}>Edit</Button></Td></tr>))}</tbody></Table>
          </Card>
        </div>
      </div>
      <Dialog open={!!branch} onOpenChange={(o) => !o && setBranch(null)} title={branch?.id ? "Edit branch" : "Add branch"}>
        {branch && <form className="space-y-4" onSubmit={async (e) => {
          e.preventDefault();
          try { await api(branch.id ? `/admin/branches/${branch.id}` : "/admin/branches", { method: branch.id ? "PUT" : "POST", json: { name: branch.name, city: branch.city, address: branch.address, is_active: branch.is_active } }); toast.success("Branch saved"); setBranch(null); reload(); }
          catch (err: any) { toast.error(err.message); }
        }}>
          <Field label="Name"><Input required value={branch.name} onChange={(e) => setBranch({ ...branch, name: e.target.value })} /></Field>
          <Field label="City"><Input value={branch.city} onChange={(e) => setBranch({ ...branch, city: e.target.value })} /></Field>
          <Field label="Address"><Input value={branch.address} onChange={(e) => setBranch({ ...branch, address: e.target.value })} /></Field>
          <Check label="Active" checked={branch.is_active} onChange={(x) => setBranch({ ...branch, is_active: x })} />
          <div className="flex justify-end gap-2"><Button type="button" variant="outline" onClick={() => setBranch(null)}>Cancel</Button><Button type="submit" variant="primary">Save branch</Button></div>
        </form>}
      </Dialog>
    </>
  );
}
