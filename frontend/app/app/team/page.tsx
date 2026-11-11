"use client";
import { useState } from "react";
import { toast } from "sonner";
import { KeyRound, Plus } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useFetch } from "@/lib/use-fetch";
import { fmtDate, ROLE_LABEL } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { Check, Field, Input, Select } from "@/components/ui/input";
import { Table, Td, Th } from "@/components/ui/table";
import { Loading, PageHeader } from "@/components/app/bits";

const ROLES = ["hospital_admin", "ophthalmologist", "technician", "receptionist"];
const blank = { email: "", full_name: "", role: "technician", phone: "", medical_registration_no: "", branch_id: "", is_active: true };

export default function Team() {
  const { me } = useAuth();
  const { data, loading, reload } = useFetch<any[]>("/admin/users");
  const branches = useFetch<any[]>("/admin/branches");
  const [edit, setEdit] = useState<any>(null);
  const [secret, setSecret] = useState<{ who: string; pw: string } | null>(null);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    const body = { ...edit, branch_id: edit.branch_id || null };
    try {
      if (edit.id) { await api(`/admin/users/${edit.id}`, { method: "PUT", json: body }); toast.success("User updated"); }
      else { const u = await api<any>("/admin/users", { method: "POST", json: body }); setSecret({ who: u.email, pw: u.temporary_password }); }
      setEdit(null); reload();
    } catch (err: any) { toast.error(err.message); }
  }
  async function reset(u: any) {
    if (!confirm(`Reset the password for ${u.full_name}? Their sessions will end.`)) return;
    try { const r = await api<any>(`/admin/users/${u.id}/reset-password`, { method: "POST" }); setSecret({ who: u.email, pw: r.temporary_password }); }
    catch (err: any) { toast.error(err.message); }
  }

  return (
    <>
      <PageHeader title="Team" description="Staff accounts for your hospital. New users receive a temporary password and must set their own on first sign-in."
        actions={<Button variant="primary" onClick={() => setEdit({ ...blank })}><Plus />Add user</Button>} />
      <Card>
        {loading ? <Loading /> : (
          <Table>
            <thead><tr><Th>Name</Th><Th>Role</Th><Th>Branch</Th><Th>Last sign-in</Th><Th>Status</Th><Th /></tr></thead>
            <tbody>{data?.map((u) => (
              <tr key={u.id}>
                <Td><span className="font-medium text-navy">{u.full_name}</span><div className="text-xs text-slate">{u.email}</div></Td>
                <Td>{ROLE_LABEL[u.role]}{u.medical_registration_no && <div className="text-xs text-slate">Reg. {u.medical_registration_no}</div>}</Td>
                <Td className="text-slate">{branches.data?.find((b) => b.id === u.branch_id)?.name ?? "—"}</Td>
                <Td className="text-slate">{fmtDate(u.last_login_at, true)}</Td>
                <Td>{u.is_active ? <Badge tone="ok">Active</Badge> : <Badge>Deactivated</Badge>}</Td>
                <Td className="whitespace-nowrap text-right">
                  <Button size="sm" variant="ghost" onClick={() => setEdit({ ...u, branch_id: u.branch_id ?? "" })}>Edit</Button>
                  {u.id !== me?.user.id && <Button size="sm" variant="ghost" onClick={() => reset(u)}><KeyRound />Reset password</Button>}
                </Td>
              </tr>))}</tbody>
          </Table>
        )}
      </Card>
      <Dialog open={!!edit} onOpenChange={(o) => !o && setEdit(null)} title={edit?.id ? "Edit user" : "Add user"}>
        {edit && <form onSubmit={save} className="space-y-4">
          {!edit.id && <Field label="Work email"><Input type="email" required value={edit.email} onChange={(e) => setEdit({ ...edit, email: e.target.value })} /></Field>}
          <Field label="Full name"><Input required value={edit.full_name} onChange={(e) => setEdit({ ...edit, full_name: e.target.value })} /></Field>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Role"><Select value={edit.role} disabled={edit.id === me?.user.id} onChange={(e) => setEdit({ ...edit, role: e.target.value })}>{ROLES.map((r) => <option key={r} value={r}>{ROLE_LABEL[r]}</option>)}</Select></Field>
            <Field label="Branch"><Select value={edit.branch_id} onChange={(e) => setEdit({ ...edit, branch_id: e.target.value })}><option value="">All branches</option>{branches.data?.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}</Select></Field>
          </div>
          <Field label="Phone"><Input value={edit.phone} onChange={(e) => setEdit({ ...edit, phone: e.target.value })} /></Field>
          {edit.role === "ophthalmologist" && <Field label="Medical council registration number" hint="Printed on signed reports. Required to sign."><Input required value={edit.medical_registration_no} onChange={(e) => setEdit({ ...edit, medical_registration_no: e.target.value })} /></Field>}
          {edit.id && edit.id !== me?.user.id && <Check label="Account active" checked={edit.is_active} onChange={(x) => setEdit({ ...edit, is_active: x })} />}
          <div className="flex justify-end gap-2"><Button type="button" variant="outline" onClick={() => setEdit(null)}>Cancel</Button><Button type="submit" variant="primary">{edit.id ? "Save changes" : "Create user"}</Button></div>
        </form>}
      </Dialog>
      <Dialog open={!!secret} onOpenChange={(o) => !o && setSecret(null)} title="Temporary password" description={`Share this with ${secret?.who} through a secure channel. It is shown only once.`}>
        <p className="rounded-md bg-mist px-4 py-3 font-mono text-lg text-navy">{secret?.pw}</p>
        <div className="mt-4 flex justify-end"><Button onClick={() => { navigator.clipboard?.writeText(secret?.pw ?? ""); toast.success("Copied"); }}>Copy</Button></div>
      </Dialog>
    </>
  );
}
