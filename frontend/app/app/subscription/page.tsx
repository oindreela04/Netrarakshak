"use client";
import Link from "next/link";
import { useFetch } from "@/lib/use-fetch";
import { fmtDate, inr } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { Table, Td, Th } from "@/components/ui/table";
import { Empty, Loading, PageHeader } from "@/components/app/bits";

function Meter({ label, used, limit }: { label: string; used: number; limit: number }) {
  const p = limit ? Math.min(100, (used / limit) * 100) : 0;
  return (
    <div>
      <div className="flex justify-between text-sm"><span className="text-slate">{label}</span><span className="tabular font-medium">{used} / {limit || "Unlimited"}</span></div>
      <div className="mt-1.5 h-2 rounded-full bg-mist"><div className={`h-full rounded-full ${p > 90 ? "bg-danger" : p > 75 ? "bg-warn" : "bg-teal"}`} style={{ width: `${limit ? p : 4}%` }} /></div>
    </div>
  );
}

export default function Subscription() {
  const { data: d, loading } = useFetch<any>("/admin/subscription");
  if (loading || !d) return <Loading />;
  return (
    <>
      <PageHeader title="Subscription" actions={<Button asChild variant="outline"><Link href="/contact">Change plan</Link></Button>} />
      <div className="grid gap-6 lg:grid-cols-[1fr_1.2fr]">
        <Card>
          <CardHeader title={`${d.plan.name} plan`} description={d.plan.description}
            action={<Badge tone={d.licence_status === "active" ? "ok" : d.licence_status === "trial" ? "blue" : "danger"}>Licence {d.licence_status}</Badge>} />
          <CardBody className="space-y-2 text-sm">
            <p><span className="text-slate">Price: </span>{d.plan.monthly_price_inr ? `${inr(d.billing_cycle === "annual" ? d.plan.annual_price_inr : d.plan.monthly_price_inr)} per ${d.billing_cycle === "annual" ? "year" : "month"} + GST` : "Custom contract"}</p>
            <p><span className="text-slate">Licence key: </span><span className="font-mono">{d.licence_key}</span></p>
            <p><span className="text-slate">Valid until: </span>{fmtDate(d.licence_expires_at)}</p>
            <ul className="mt-3 grid grid-cols-2 gap-1 text-xs text-slate">{Object.entries(d.plan.features).map(([k, v]) => <li key={k}>{k.replaceAll("_", " ")}: <b className="text-ink">{v === true ? "Included" : v === false ? "—" : String(v)}</b></li>)}</ul>
          </CardBody>
        </Card>
        <Card>
          <CardHeader title="Usage this month" />
          <CardBody className="space-y-5">
            <Meter label="Screenings" used={d.usage.screenings_this_month} limit={d.usage.screenings_limit} />
            <Meter label="Active users" used={d.usage.active_users} limit={d.usage.users_limit} />
            <Meter label="Branches" used={d.usage.branches} limit={d.usage.branches_limit} />
          </CardBody>
        </Card>
      </div>
      <Card className="mt-6">
        <CardHeader title="Invoices" description="GST invoices issued by NetraRakshak" />
        {!d.invoices.length ? <Empty title="No invoices yet" /> : (
          <Table>
            <thead><tr><Th>Invoice</Th><Th>Period</Th><Th>Subtotal</Th><Th>GST</Th><Th>Total</Th><Th>Status</Th></tr></thead>
            <tbody>{d.invoices.map((i: any) => (
              <tr key={i.id}><Td className="tabular">{i.invoice_number}</Td><Td className="text-slate">{fmtDate(i.period_start)} – {fmtDate(i.period_end)}</Td>
                <Td className="tabular">{inr(i.subtotal_inr)}</Td><Td className="tabular">{inr(i.gst_inr)}</Td><Td className="tabular font-semibold">{inr(i.total_inr)}</Td>
                <Td><Badge tone={i.status === "paid" ? "ok" : "warn"}>{i.status}</Badge></Td></tr>))}</tbody>
          </Table>
        )}
      </Card>
    </>
  );
}
