import { Reveal } from "./motion";

export function PageHero({ title, intro }: { title: string; intro: string }) {
  return (
    <section className="relative overflow-hidden border-b border-line bg-gradient-to-b from-[#F4F8FC] to-white pt-16">
      <div className="pointer-events-none absolute -right-40 -top-40 h-[560px] w-[560px] rounded-full bg-[radial-gradient(circle,rgba(47,134,214,0.14),transparent_65%)]" />
      <div className="pointer-events-none absolute -left-24 bottom-[-180px] h-[380px] w-[380px] rounded-full bg-[radial-gradient(circle,rgba(62,142,138,0.12),transparent_65%)]" />
      <Reveal className="relative mx-auto max-w-6xl px-5 py-20 sm:px-8">
        <h1 className="max-w-3xl font-hero text-[40px] font-light leading-[1.06] text-navy sm:text-[54px]">{title}</h1>
        <p className="mt-6 max-w-2xl text-[17px] leading-7 text-ink/70">{intro}</p>
      </Reveal>
    </section>
  );
}

export function Prose({ children }: { children: React.ReactNode }) {
  return <div className="mx-auto max-w-3xl space-y-5 px-5 py-16 text-[16px] leading-7 text-ink/80 sm:px-8 [&_h2]:mt-12 [&_h2]:font-hero [&_h2]:text-[28px] [&_h2]:font-normal [&_h2]:text-navy [&_li]:ml-5 [&_li]:list-disc [&_strong]:text-navy">{children}</div>;
}

export function FormPanel({ children }: { children: React.ReactNode }) {
  return <section className="mx-auto max-w-3xl px-5 py-16 sm:px-8"><div className="rounded-2xl border border-line bg-white p-6 shadow-[0_12px_40px_rgba(11,31,58,0.08)] sm:p-8">{children}</div></section>;
}
