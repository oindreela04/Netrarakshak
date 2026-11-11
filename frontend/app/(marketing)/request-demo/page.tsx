import type { Metadata } from "next";
import { EnquiryForm } from "@/components/marketing/enquiry-form";
import { FormPanel, PageHero } from "@/components/marketing/page-hero";
export const metadata: Metadata = { title: "Request a demo" };

export default function RequestDemo() {
  return (
    <>
      <PageHero title="Request a demo" intro="We will walk your team through a complete screening — registration, capture, quality check, AI analysis, review and report — using synthetic data." />
      <FormPanel><EnquiryForm kind="demo" /></FormPanel>
    </>
  );
}
