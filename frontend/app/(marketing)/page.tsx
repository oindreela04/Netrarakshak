import Link from "next/link";
import {
  Activity, ClipboardCheck, FileText, Fingerprint, Gauge, Hospital, Layers, Lock, Microscope, ScanEye, ShieldCheck, Stethoscope, Users,
} from "lucide-react";
import { Reveal, Tilt } from "@/components/marketing/motion";
import { ScrollHero } from "@/components/marketing/scroll-hero";
import { Button } from "@/components/ui/button";

const STEPS = [
  { t: "Register the patient", d: "Reception records demographics, diabetes and hypertension history, medications and written or digital consent." },
  { t: "Capture both eyes", d: "A technician photographs each eye on a compatible fundus camera and uploads the right- and left-eye images." },
  { t: "Check image quality", d: "Every photograph is checked for focus, exposure, field of view and artefacts. Poor images are flagged for recapture with the reason." },
  { t: "Run AI screening", d: "Gradable images are analysed by the diabetic retinopathy model. Uncertain cases are marked inconclusive, never forced into a grade." },
  { t: "Ophthalmologist review", d: "The doctor inspects images and heatmaps, accepts, modifies or rejects the AI suggestion, and signs with their credentials." },
  { t: "Report and follow up", d: "A branded PDF report is issued, stored in the patient's history and the dashboard updates for follow-up and referral tracking." },
];

const FEATURES = [
  { i: ScanEye, t: "Fundus image viewer", d: "Zoom, pan, side-by-side eyes and Grad-CAM overlays, clearly separated from confirmed findings." },
  { i: Gauge, t: "Automatic quality gate", d: "Ten checks run before any AI inference, so ungradable images never produce a result." },
  { i: Stethoscope, t: "Separate clinician workspace", d: "Prioritised review queue, structured grading, referral and recapture requests." },
  { i: FileText, t: "Hospital-branded reports", d: "Signed PDF reports with images, quality, AI output, model version and the doctor's interpretation." },
  { i: Layers, t: "Independent disease modules", d: "Diabetic retinopathy first. Glaucoma, AMD and hypertensive retinopathy activate only when separately validated." },
  { i: Activity, t: "Operational analytics", d: "Screening volume, recapture rate, referrals, turnaround time and clinician–AI agreement." },
];

const card = "rounded-2xl border border-line bg-white p-6 shadow-[0_1px_2px_rgba(11,31,58,0.04),0_8px_24px_rgba(11,31,58,0.05)]";
const h2 = "font-hero text-[34px] font-light leading-tight text-navy sm:text-[42px]";

export default function Home() {
  return (
    <>
      <ScrollHero />

      {/* Introduction */}
      <section className="mx-auto max-w-6xl px-5 py-28 sm:px-6">
        <div className="grid gap-12 lg:grid-cols-[1fr_1.2fr]">
          <Reveal><h2 className={h2}>Diabetic eye disease is often silent until sight is at risk.</h2></Reveal>
          <Reveal delay={120} className="space-y-5 text-[16px] leading-7 text-ink/75">
            <p>Regular retinal screening of people with diabetes finds treatable disease early, but specialist time is scarce and
              screening volumes are high. NetraRakshak lets trained staff capture and prepare every case so that ophthalmologists
              spend their time on interpretation, not administration.</p>
            <p>The AI never has the last word. Every result is a suggestion with its confidence, its limitations and a heatmap of
              what influenced it. When the model is unsure, or the image is unsuitable, the case is marked
              <strong className="font-semibold text-navy"> inconclusive — human review required</strong>.</p>
          </Reveal>
        </div>
      </section>

      {/* How it works */}
      <section id="how" className="scroll-mt-16 border-y border-line bg-mist">
        <div className="mx-auto max-w-6xl px-5 py-28 sm:px-6">
          <Reveal><h2 className={h2}>How a screening flows</h2>
            <p className="mt-3 max-w-2xl text-ink/65">Six steps, each owned by the right person, each recorded in the audit trail.</p></Reveal>
          <ol className="mt-14 grid gap-5 md:grid-cols-3">
            {STEPS.map((s, i) => (
              <Reveal as="li" key={s.t} delay={(i % 3) * 110}>
                <Tilt className={`${card} h-full`}>
                  <span className="font-hero text-4xl font-light text-clinical">{i + 1}</span>
                  <h3 className="mt-4 font-semibold text-navy">{s.t}</h3>
                  <p className="mt-2 text-sm leading-6 text-ink/65">{s.d}</p>
                </Tilt>
              </Reveal>
            ))}
          </ol>
        </div>
      </section>

      {/* Features */}
      <section className="mx-auto max-w-6xl px-5 py-28 sm:px-6">
        <Reveal><h2 className={h2}>Built for the screening room and the consulting room</h2></Reveal>
        <div className="mt-14 grid gap-x-12 gap-y-12 md:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map(({ i: Icon, t, d }, k) => (
            <Reveal key={t} delay={(k % 3) * 110} className="border-l-2 border-teal/60 pl-5">
              <Icon className="h-5 w-5 text-clinical" />
              <h3 className="mt-3 font-semibold text-navy">{t}</h3>
              <p className="mt-1.5 text-sm leading-6 text-ink/65">{d}</p>
            </Reveal>
          ))}
        </div>
      </section>

      {/* AI technology */}
      <section className="border-y border-line bg-gradient-to-br from-clinical-50 via-white to-teal-50">
        <div className="mx-auto grid max-w-6xl gap-12 px-5 py-28 sm:px-6 lg:grid-cols-2">
          <Reveal>
            <h2 className={h2}>AI you can inspect, not just trust</h2>
            <p className="mt-5 leading-7 text-ink/75">
              Each disease has its own model, its own training data and its own evaluation. The diabetic retinopathy module grades the
              five-level international clinical scale with calibrated confidence and Grad-CAM heatmaps. Every model ships with a model
              card: data source and licence, held-out test metrics and known limitations.
            </p>
            <Button asChild variant="outline" className="mt-8 rounded-full bg-white px-6"><Link href="/technology">How the AI works</Link></Button>
          </Reveal>
          <Reveal delay={150}>
            <Tilt className={card}>
              <p className="text-sm font-semibold text-teal-700">Current model status</p>
              <dl className="mt-4 divide-y divide-line text-sm">
                {[
                  ["Diabetic retinopathy", "Active. EfficientNet-B0 trained on APTOS 2019; held-out referable-DR sensitivity 82.0%, specificity 96.6%. Not clinically validated."],
                  ["Glaucoma suspect", "Architecture defined. Not active."],
                  ["Age-related macular degeneration", "Architecture defined. Not active."],
                  ["Hypertensive retinopathy", "Architecture defined. Not active."],
                  ["Clinical validation", "Not yet performed. Prospective validation in Indian clinical settings is planned."],
                ].map(([k, v]) => (
                  <div key={k} className="grid gap-1 py-3 sm:grid-cols-[180px_1fr]"><dt className="font-medium text-navy">{k}</dt><dd className="text-ink/65">{v}</dd></div>
                ))}
              </dl>
            </Tilt>
          </Reveal>
        </div>
      </section>

      {/* Solutions */}
      <section className="mx-auto max-w-6xl px-5 py-28 sm:px-6">
        <Reveal><h2 className={h2}>One platform, from a single clinic to a hospital network</h2></Reveal>
        <div className="mt-12 grid gap-5 md:grid-cols-3">
          {[
            { i: Microscope, t: "Eye clinics", d: "A complete screening and reporting workflow without IT overhead. Works with the fundus camera you already own." },
            { i: Hospital, t: "Hospitals", d: "Diabetes OPD screening with ophthalmology review queues, referral tracking and hospital-branded reports." },
            { i: Users, t: "Hospital networks", d: "Multiple branches under one account with central analytics, role-based teams and dedicated hosting." },
          ].map(({ i: Icon, t, d }, k) => (
            <Reveal key={t} delay={k * 110}>
              <Tilt className={`${card} h-full`}><Icon className="h-6 w-6 text-teal" /><h3 className="mt-4 text-lg font-semibold text-navy">{t}</h3><p className="mt-2 text-sm leading-6 text-ink/65">{d}</p></Tilt>
            </Reveal>
          ))}
        </div>
      </section>

      {/* Security */}
      <section className="border-y border-line bg-mist">
        <div className="mx-auto grid max-w-6xl gap-12 px-5 py-28 sm:px-6 lg:grid-cols-[1fr_1.4fr]">
          <Reveal>
            <h2 className={h2}>Patient data stays inside your hospital&apos;s walls</h2>
            <Button asChild variant="outline" className="mt-8 rounded-full bg-white px-6"><Link href="/security">Security details</Link></Button>
          </Reveal>
          <ul className="grid gap-8 sm:grid-cols-2">
            {[
              { i: Lock, t: "Encrypted at rest and in transit", d: "Images and reports are encrypted before storage; all traffic uses TLS." },
              { i: Fingerprint, t: "Role-based access", d: "Five roles with least-privilege permissions. Platform staff cannot see patient records." },
              { i: ShieldCheck, t: "Tamper-evident audit trail", d: "Every view, upload, AI run and signature is logged in a hash-chained record." },
              { i: ClipboardCheck, t: "Consent and retention", d: "Recorded consent per purpose, configurable retention and verified secure erasure." },
            ].map(({ i: Icon, t, d }, k) => (
              <Reveal as="li" key={t} delay={(k % 2) * 110} className="flex gap-3">
                <Icon className="mt-0.5 h-5 w-5 shrink-0 text-clinical" /><div><p className="font-semibold text-navy">{t}</p><p className="mt-1 text-sm leading-6 text-ink/65">{d}</p></div>
              </Reveal>
            ))}
          </ul>
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="mx-auto max-w-6xl scroll-mt-16 px-5 py-28 sm:px-6">
        <Reveal><h2 className={h2}>Plans</h2><p className="mt-3 text-ink/65">Prices exclude GST. Annual billing available.</p></Reveal>
        <div className="mt-12 grid gap-6 md:grid-cols-3">
          {[
            { n: "Starter", who: "Small eye clinics", p: "₹14,999", u: "/month", f: ["300 screenings a month", "5 users, 1 site", "DR screening and PDF reports", "Email support"] },
            { n: "Professional", who: "Medium hospitals", p: "₹39,999", u: "/month", f: ["1,500 screenings a month", "25 users, up to 3 branches", "Hospital branding and advanced analytics", "Fundus camera integration", "Priority support"], hl: true },
            { n: "Enterprise", who: "Multi-branch networks", p: "Custom", u: "", f: ["Unlimited screenings and branches", "Single sign-on and dedicated hosting", "Audit export and SLA", "24×7 support"] },
          ].map((pl, k) => (
            <Reveal key={pl.n} delay={k * 110}>
              <Tilt className={`${card} h-full ${pl.hl ? "border-2 border-clinical" : ""}`}>
                <p className="font-semibold text-navy">{pl.n}</p>
                <p className="text-sm text-ink/60">{pl.who}</p>
                <p className="mt-6"><span className="font-hero text-4xl font-light text-navy">{pl.p}</span><span className="text-sm text-ink/60">{pl.u}</span></p>
                <ul className="mt-6 space-y-2 text-sm text-ink/75">{pl.f.map((x) => <li key={x} className="flex gap-2"><span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-teal" />{x}</li>)}</ul>
                <Button asChild variant={pl.hl ? "primary" : "outline"} className="mt-7 w-full rounded-full"><Link href="/request-demo">Talk to us</Link></Button>
              </Tilt>
            </Reveal>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="border-t border-line bg-gradient-to-r from-clinical to-teal">
        <Reveal className="mx-auto flex max-w-6xl flex-col items-start justify-between gap-8 px-5 py-20 sm:px-6 md:flex-row md:items-center">
          <h2 className="max-w-xl font-hero text-[30px] font-light leading-tight text-white sm:text-[36px]">See NetraRakshak with your own screening workflow.</h2>
          <Button asChild size="lg" variant="inverse" className="rounded-full px-7"><Link href="/request-demo">Request a demo</Link></Button>
        </Reveal>
      </section>
    </>
  );
}
