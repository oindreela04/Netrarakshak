"use client";
import { useState } from "react";
import { toast } from "sonner";
import { Plus, ShieldCheck } from "lucide-react";
import { api } from "@/lib/api";
import { useFetch } from "@/lib/use-fetch";
import { fmtDate, inr } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardHeader } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { Check, Field, Input, Select, Textarea } from "@/components/ui/input";
import { Table, Td, Th } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Loading, PageHeader, Stat } from "@/components/app/bits";

const LIC_TONE: Record<string, any> = { active: "ok", trial: "blue", suspended: "danger", expired: "warn" };

export default function Platform() {
  const stats = useFetch<any>("/platform/stats");
  const hospitals = useFetch<any[]>("/platform/hospitals");
  const plans = useFetch<any[]>("/platform/plans");
  const invoices = useFetch<any[]>("/platform/invoices");
  const enquiries = useFetch<any[]>("/platform/enquiries");
  const [edit, setEdit] = useState<any>(null);
  const [onboard, setOnboard] = useState<any>(null);
  const [plan, setPlan] = useState<any>(null);
  const [created, setCreated] = useState<any>(null);

  const refresh = () => { stats.reload(); hospitals.reload(); invoices.reload(); plans.reload(); };
  const call = async (fn: () => Promise<any>, ok: string) => { try { const r = await fn(); toast.success(ok); refresh(); return r; } catch (e: any) { toast.error(e.message); } };
  const s = stats.data;

  return (
    <>
      <PageHeader title="Platform console" description="Tenants, plans, licences and billing. Patient records are not accessible from this console."
        actions={<>
          <Button variant="outline" onClick={async () => { const r = await api<any>("/platform/audit/verify"); r.valid ? toast.success(`Audit chain intact (${r.checked} entries)`) : toast.error(`Audit chain broken at entry ${r.broken_at_id}`); }}><ShieldCheck />Verify audit chain</Button>
          <Button variant="primary" onClick={() => setOnboard({ name: "", code: "", city: "", state: "", email: "", phone: "", plan_code: "STARTER", billing_cycle: "monthly", licence_status: "trial", admin_email: "", admin_name: "" })}><Plus />Onboard hospital</Button>
        </>} />
      {!s ? <Loading /> : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
          <Stat label="Hospitals" value={s.hospitals} sub={`${s.active_licences} active · ${s.trials} trial`} />
          <Stat label="Monthly recurring revenue" value={inr(s.mrr_inr)} sub="Active licences, excl. GST" />
          <Stat label="Users" value={s.users} />
          <Stat label="Screenings (all time)" value={s.screenings} sub={`${s.reports} reports`} />
          <Stat label="Open enquiries" value={s.open_enquiries} />
        </div>
      )}

      <Tabs defaultValue="hospitals" className="mt-6">
        <TabsList><TabsTrigger value="hospitals">Hospitals</TabsTrigger><TabsTrigger value="plans">Plans</TabsTrigger><TabsTrigger value="invoices">Invoices</TabsTrigger><TabsTrigger value="enquiries">Enquiries</TabsTrigger></TabsList>
        <TabsContent value="hospitals" className="pt-5">
          <Card>
            <Table>
              <thead><tr><Th>Hospital</Th><Th>Plan</Th><Th>Licence</Th><Th>Usage (month)</Th><Th>Created</Th><Th /></tr></thead>
              <tbody>{hospitals.data?.map((h) => (
                <tr key={h.id}>
                  <Td><span className="font-medium text-navy">{h.name}</span><div className="text-xs text-slate">{h.code} · {h.city}{!h.is_active && " · deactivated"}</div></Td>
                  <Td>{h.plan_code}<div className="text-xs text-slate">{h.billing_cycle}</div></Td>
                  <Td><Badge tone={LIC_TONE[h.licence_status]}>{h.licence_status}</Badge><div className="mt-1 text-xs text-slate">until {fmtDate(h.licence_expires_at)}</div></Td>
                  <Td className="text-xs text-slate">{h.usage.screenings_this_month} screenings · {h.usage.users} users · {h.usage.branches} branches</Td>
                  <Td className="text-slate">{fmtDate(h.created_at)}</Td>
                  <Td className="whitespace-nowrap text-right">
                    <Button size="sm" variant="ghost" onClick={() => setEdit({ ...h, licence_expires_at: h.licence_expires_at?.slice(0, 10) ?? "" })}>Manage</Button>
                    <Button size="sm" variant="ghost" onClick={() => call(() => api(`/platform/hospitals/${h.id}/invoices`, { method: "POST" }), "Invoice issued")}>Issue invoice</Button>
                  </Td>
                </tr>))}</tbody>
            </Table>
          </Card>
        </TabsContent>
        <TabsContent value="plans" className="pt-5">
          <Card>
            <Table>
              <thead><tr><Th>Plan</Th><Th>Monthly</Th><Th>Annual</Th><Th>Screenings / month</Th><Th>Users</Th><Th>Branches</Th><Th /></tr></thead>
              <tbody>{plans.data?.map((p) => (
                <tr key={p.code}><Td><span className="font-medium text-navy">{p.name}</span><div className="text-xs text-slate">{p.description}</div></Td>
                  <Td className="tabular">{p.monthly_price_inr ? inr(p.monthly_price_inr) : "Custom"}</Td><Td className="tabular">{p.annual_price_inr ? inr(p.annual_price_inr) : "Custom"}</Td>
                  <Td className="tabular">{p.max_screenings_per_month || "Unlimited"}</Td><Td className="tabular">{p.max_users || "Unlimited"}</Td><Td className="tabular">{p.max_branches || "Unlimited"}</Td>
                  <Td className="text-right"><Button size="sm" variant="ghost" onClick={() => setPlan({ ...p, features: JSON.stringify(p.features, null, 2) })}>Edit</Button></Td></tr>))}</tbody>
            </Table>
          </Card>
        </TabsContent>
        <TabsContent value="invoices" className="pt-5">
          <Card>
            <Table>
              <thead><tr><Th>Invoice</Th><Th>Hospital</Th><Th>Period</Th><Th>Total</Th><Th>Status</Th><Th /></tr></thead>
              <tbody>{invoices.data?.map((i) => (
                <tr key={i.id}><Td className="tabular">{i.invoice_number}</Td><Td>{i.hospital}</Td><Td className="text-slate">{fmtDate(i.period_start)} – {fmtDate(i.period_end)}</Td>
                  <Td className="tabular font-semibold">{inr(i.total_inr)}</Td>
                  <Td><Badge tone={i.status === "paid" ? "ok" : "warn"}>{i.status}</Badge>{i.payment_reference && <div className="text-xs text-slate">{i.payment_reference}</div>}</Td>
                  <Td className="text-right">{i.status !== "paid" && <Button size="sm" variant="ghost" onClick={() => { const ref = prompt("Payment reference (UTR / cheque number)"); if (ref) call(() => api(`/platform/invoices/${i.id}/paid`, { method: "POST", json: { reference: ref } }), "Marked paid; licence extended"); }}>Mark paid</Button>}</Td></tr>))}</tbody>
            </Table>
            {!invoices.data?.length && <p className="p-6 text-sm text-slate">No invoices issued yet.</p>}
          </Card>
        </TabsContent>
        <TabsContent value="enquiries" className="pt-5">
          <Card>
            <Table>
              <thead><tr><Th>Received</Th><Th>Contact</Th><Th>Type</Th><Th>Message</Th><Th>Status</Th></tr></thead>
              <tbody>{enquiries.data?.map((d) => (
                <tr key={d.id} className="align-top"><Td className="whitespace-nowrap text-slate">{fmtDate(d.created_at, true)}</Td>
                  <Td><span className="font-medium text-navy">{d.name}</span><div className="text-xs text-slate">{d.organisation}<br />{d.email} {d.phone}</div></Td>
                  <Td>{d.kind}</Td><Td className="max-w-md text-xs">{d.message}</Td>
                  <Td><Select className="h-8 w-32 text-xs" value={d.status} onChange={async (e) => { await api(`/platform/enquiries/${d.id}/status/${e.target.value}`, { method: "POST" }); enquiries.reload(); stats.reload(); }}>
                    <option value="new">New</option><option value="contacted">Contacted</option><option value="closed">Closed</option></Select></Td></tr>))}</tbody>
            </Table>
            {!enquiries.data?.length && <p className="p-6 text-sm text-slate">No enquiries yet.</p>}
          </Card>
        </TabsContent>
      </Tabs>

      <Dialog open={!!edit} onOpenChange={(o) => !o && setEdit(null)} title={`Manage ${edit?.name ?? ""}`}>
        {edit && <form className="space-y-4" onSubmit={async (e) => { e.preventDefault(); await call(() => api(`/platform/hospitals/${edit.id}`, { method: "PUT", json: { plan_code: edit.plan_code, billing_cycle: edit.billing_cycle, licence_status: edit.licence_status, is_active: edit.is_active, licence_expires_at: edit.licence_expires_at ? `${edit.licence_expires_at}T23:59:59+05:30` : null } }), "Hospital updated"); setEdit(null); }}>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Plan"><Select value={edit.plan_code} onChange={(e) => setEdit({ ...edit, plan_code: e.target.value })}>{plans.data?.map((p) => <option key={p.code} value={p.code}>{p.name}</option>)}</Select></Field>
            <Field label="Billing cycle"><Select value={edit.billing_cycle} onChange={(e) => setEdit({ ...edit, billing_cycle: e.target.value })}><option value="monthly">Monthly</option><option value="annual">Annual</option></Select></Field>
            <Field label="Licence status"><Select value={edit.licence_status} onChange={(e) => setEdit({ ...edit, licence_status: e.target.value })}>{["trial", "active", "suspended", "expired"].map((x) => <option key={x}>{x}</option>)}</Select></Field>
            <Field label="Licence valid until"><Input type="date" value={edit.licence_expires_at} onChange={(e) => setEdit({ ...edit, licence_expires_at: e.target.value })} /></Field>
          </div>
          <Check label="Hospital account active (deactivating blocks all sign-ins)" checked={edit.is_active} onChange={(x) => setEdit({ ...edit, is_active: x })} />
          <div className="flex justify-end gap-2"><Button type="button" variant="outline" onClick={() => setEdit(null)}>Cancel</Button><Button type="submit" variant="primary">Save</Button></div>
        </form>}
      </Dialog>

      <Dialog open={!!onboard} onOpenChange={(o) => !o && setOnboard(null)} title="Onboard hospital" description="Creates the tenant, a main branch and the first hospital administrator." wide>
        {onboard && <form className="grid gap-4 sm:grid-cols-2" onSubmit={async (e) => { e.preventDefault(); const r = await call(() => api("/platform/hospitals", { method: "POST", json: onboard }), "Hospital created"); if (r) { setCreated(r); setOnboard(null); } }}>
          <Field label="Hospital name" className="sm:col-span-2"><Input required value={onboard.name} onChange={(e) => setOnboard({ ...onboard, name: e.target.value })} /></Field>
          <Field label="Short code" hint="2–8 capitals/digits, used in patient IDs"><Input required pattern="[A-Z0-9]{2,8}" value={onboard.code} onChange={(e) => setOnboard({ ...onboard, code: e.target.value.toUpperCase() })} /></Field>
          <Field label="Plan"><Select value={onboard.plan_code} onChange={(e) => setOnboard({ ...onboard, plan_code: e.target.value })}>{plans.data?.map((p) => <option key={p.code} value={p.code}>{p.name}</option>)}</Select></Field>
          <Field label="City"><Input value={onboard.city} onChange={(e) => setOnboard({ ...onboard, city: e.target.value })} /></Field>
          <Field label="State"><Input value={onboard.state} onChange={(e) => setOnboard({ ...onboard, state: e.target.value })} /></Field>
          <Field label="Administrator name"><Input required value={onboard.admin_name} onChange={(e) => setOnboard({ ...onboard, admin_name: e.target.value })} /></Field>
          <Field label="Administrator email"><Input required type="email" value={onboard.admin_email} onChange={(e) => setOnboard({ ...onboard, admin_email: e.target.value })} /></Field>
          <div className="flex justify-end gap-2 sm:col-span-2"><Button type="button" variant="outline" onClick={() => setOnboard(null)}>Cancel</Button><Button type="submit" variant="primary">Create hospital</Button></div>
        </form>}
      </Dialog>

      <Dialog open={!!created} onOpenChange={(o) => !o && setCreated(null)} title="Hospital created" description="Send the administrator their temporary password through a secure channel. It is shown only once.">
        <p className="text-sm">{created?.name} · licence {created?.licence_key}</p>
        <p className="mt-3 rounded-md bg-mist px-4 py-3 font-mono text-lg text-navy">{created?.admin_temporary_password}</p>
      </Dialog>

      <Dialog open={!!plan} onOpenChange={(o) => !o && setPlan(null)} title={`Edit ${plan?.name ?? ""} plan`} description="Use 0 for unlimited limits or custom pricing.">
        {plan && <form className="grid gap-4 sm:grid-cols-2" onSubmit={async (e) => {
          e.preventDefault();
          let features; try { features = JSON.parse(plan.features); } catch { return toast.error("Features must be valid JSON"); }
          await call(() => api(`/platform/plans/${plan.code}`, { method: "PUT", json: { ...plan, features, monthly_price_inr: +plan.monthly_price_inr, annual_price_inr: +plan.annual_price_inr, max_screenings_per_month: +plan.max_screenings_per_month, max_users: +plan.max_users, max_branches: +plan.max_branches } }), "Plan updated");
          setPlan(null);
        }}>
          <Field label="Name"><Input value={plan.name} onChange={(e) => setPlan({ ...plan, name: e.target.value })} /></Field>
          <Field label="Description"><Input value={plan.description} onChange={(e) => setPlan({ ...plan, description: e.target.value })} /></Field>
          {(["monthly_price_inr", "annual_price_inr", "max_screenings_per_month", "max_users", "max_branches"] as const).map((k) => (
            <Field key={k} label={k.replaceAll("_", " ").replace("inr", "(₹)")}><Input type="number" min={0} value={plan[k]} onChange={(e) => setPlan({ ...plan, [k]: e.target.value })} /></Field>))}
          <Field label="Features (JSON)" className="sm:col-span-2"><Textarea className="font-mono text-xs" rows={8} value={plan.features} onChange={(e) => setPlan({ ...plan, features: e.target.value })} /></Field>
          <div className="flex justify-end gap-2 sm:col-span-2"><Button type="button" variant="outline" onClick={() => setPlan(null)}>Cancel</Button><Button type="submit" variant="primary">Save plan</Button></div>
        </form>}
      </Dialog>
    </>
  );
}
