import Link from "next/link";
import { Logo } from "@/components/brand/logo";

export function SiteFooter() {
  return (
    <footer className="border-t border-line bg-mist text-ink/70">
      <div className="mx-auto grid max-w-6xl gap-10 px-4 py-14 sm:px-6 md:grid-cols-[1.4fr_1fr_1fr_1fr]">
        <div>
          <Logo />
          <p className="mt-4 max-w-xs text-sm leading-6">See beyond the retina. Detect earlier. Protect vision.</p>
        </div>
        <FooterCol title="Product" links={[["/#how", "How it works"], ["/technology", "AI technology"], ["/#pricing", "Plans"]]} />
        <FooterCol title="Hospitals" links={[["/solutions", "Solutions"], ["/security", "Security & privacy"], ["/request-demo", "Request a demo"]]} />
        <FooterCol title="Company" links={[["/contact", "Contact"], ["/login", "Sign in"]]} />
      </div>
      <div className="border-t border-line">
        <p className="mx-auto max-w-6xl px-4 py-6 text-xs leading-5 text-slate sm:px-6">
          NetraRakshak is an investigational, clinician-supervised screening aid. It is not a standalone diagnostic device,
          has not been clinically validated, and has not been approved or registered by CDSCO or any other regulator.
          AI outputs must be reviewed by a qualified ophthalmologist. © {new Date().getFullYear()} NetraRakshak.
        </p>
      </div>
    </footer>
  );
}

function FooterCol({ title, links }: { title: string; links: [string, string][] }) {
  return (
    <div>
      <p className="text-sm font-semibold text-navy">{title}</p>
      <ul className="mt-3 space-y-2 text-sm">
        {links.map(([h, l]) => <li key={h}><Link className="hover:text-navy" href={h}>{l}</Link></li>)}
      </ul>
    </div>
  );
}
