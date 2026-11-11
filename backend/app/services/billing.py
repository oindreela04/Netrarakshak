"""Billing integration architecture.

`BillingProvider` is the seam between NetraRakshak's subscription model and a payment gateway. The default
`ManualInvoiceProvider` issues GST invoices that are settled offline (NEFT/RTGS/cheque) and marked paid by a
super-admin — the common pattern for Indian hospital B2B contracts. A gateway adapter (e.g. Razorpay
Subscriptions, Stripe) implements the same interface and is enabled via BILLING_PROVIDER + its API keys.
No gateway credentials are bundled with this repository.
"""
import os
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import Hospital, Invoice, Plan

GST_RATE = 0.18  # SaaS (SAC 998314) — confirm with your chartered accountant


class BillingProvider:
    name = "base"

    def create_invoice(self, db: Session, hospital: Hospital, plan: Plan, period_start: date) -> Invoice:
        raise NotImplementedError

    def mark_paid(self, invoice: Invoice, reference: str) -> None:
        raise NotImplementedError


class ManualInvoiceProvider(BillingProvider):
    name = "manual"

    def create_invoice(self, db, hospital, plan, period_start):
        annual = hospital.billing_cycle == "annual"
        period_end = period_start + timedelta(days=365 if annual else 30) - timedelta(days=1)
        subtotal = plan.annual_price_inr if annual else plan.monthly_price_inr
        gst = int(round(subtotal * GST_RATE))
        n = db.execute(select(func.count()).select_from(Invoice)).scalar_one() + 1
        inv = Invoice(hospital_id=hospital.id, invoice_number=f"NR-INV-{period_start:%Y%m}-{n:05d}", period_start=period_start,
                      period_end=period_end, plan_code=plan.code, subtotal_inr=subtotal, gst_inr=gst, total_inr=subtotal + gst,
                      line_items=[{"description": f"NetraRakshak {plan.name} plan ({hospital.billing_cycle})", "amount_inr": subtotal},
                                  {"description": "GST @ 18%", "amount_inr": gst}])
        db.add(inv)
        return inv

    def mark_paid(self, invoice, reference):
        from ..models import utcnow
        invoice.status, invoice.payment_reference, invoice.paid_at = "paid", reference, utcnow()


class RazorpayProvider(ManualInvoiceProvider):  # pragma: no cover - requires live credentials
    name = "razorpay"

    def __init__(self):
        self.key_id = os.getenv("RAZORPAY_KEY_ID")
        self.key_secret = os.getenv("RAZORPAY_KEY_SECRET")
        if not (self.key_id and self.key_secret):
            raise RuntimeError("RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET not configured")
    # create_invoice → POST /v1/invoices ; webhook /billing/webhook verifies X-Razorpay-Signature → mark_paid


def get_billing_provider() -> BillingProvider:
    return RazorpayProvider() if os.getenv("BILLING_PROVIDER") == "razorpay" else ManualInvoiceProvider()
