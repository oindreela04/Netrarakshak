"use client";
import { useState } from "react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useFetch } from "@/lib/use-fetch";
import { fmtDate, ROLE_LABEL } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { Field, Input } from "@/components/ui/input";
import { Table, Td, Th } from "@/components/ui/table";
import { PageHeader } from "@/components/app/bits";

export default function Settings() {
  const { me, reload } = useAuth();
  const sessions = useFetch<any[]>("/auth/sessions");
  const [pw, setPw] = useState({ current_password: "", new_password: "", confirm: "" });
  return (
    <>
      <PageHeader title="Account settings" />
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader title="Profile" description="Contact your hospital administrator to change these details." />
          <CardBody className="space-y-2 text-sm">
            <p><span className="text-slate">Name: </span>{me?.user.full_name}</p>
            <p><span className="text-slate">Email: </span>{me?.user.email}</p>
            <p><span className="text-slate">Role: </span>{ROLE_LABEL[me?.user.role ?? ""]}</p>
            {me?.user.medical_registration_no && <p><span className="text-slate">Registration number: </span>{me.user.medical_registration_no}</p>}
            {me?.hospital && <p><span className="text-slate">Hospital: </span>{me.hospital.name}</p>}
          </CardBody>
        </Card>
        <Card>
          <CardHeader title="Change password" description="At least 10 characters with upper- and lower-case letters, a digit and a symbol. Other devices are signed out." />
          <CardBody>
            <form className="space-y-4" onSubmit={async (e) => {
              e.preventDefault();
              if (pw.new_password !== pw.confirm) return toast.error("The new passwords do not match");
              try { await api("/auth/change-password", { method: "POST", json: { current_password: pw.current_password, new_password: pw.new_password } }); toast.success("Password changed"); setPw({ current_password: "", new_password: "", confirm: "" }); reload(); sessions.reload(); }
              catch (err: any) { toast.error(err.message); }
            }}>
              <Field label="Current password"><Input type="password" required autoComplete="current-password" value={pw.current_password} onChange={(e) => setPw({ ...pw, current_password: e.target.value })} /></Field>
              <Field label="New password"><Input type="password" required autoComplete="new-password" value={pw.new_password} onChange={(e) => setPw({ ...pw, new_password: e.target.value })} /></Field>
              <Field label="Confirm new password"><Input type="password" required autoComplete="new-password" value={pw.confirm} onChange={(e) => setPw({ ...pw, confirm: e.target.value })} /></Field>
              <Button type="submit" variant="primary">Change password</Button>
            </form>
          </CardBody>
        </Card>
      </div>
      <Card className="mt-6">
        <CardHeader title="Active sessions" />
        <Table>
          <thead><tr><Th>Signed in</Th><Th>Device</Th><Th>IP</Th><Th>Expires</Th><Th /></tr></thead>
          <tbody>{sessions.data?.map((s) => (
            <tr key={s.id}><Td className="text-slate">{fmtDate(s.created_at, true)}</Td><Td className="max-w-[340px] truncate text-xs text-slate">{s.user_agent}</Td><Td className="text-slate">{s.ip_address}</Td><Td className="text-slate">{fmtDate(s.expires_at)}</Td>
              <Td className="text-right">{s.current ? <Badge tone="teal">This session</Badge> : <Button size="sm" variant="ghost" onClick={async () => { await api(`/auth/sessions/${s.id}`, { method: "DELETE" }); sessions.reload(); }}>Sign out</Button>}</Td></tr>))}</tbody>
        </Table>
      </Card>
    </>
  );
}
