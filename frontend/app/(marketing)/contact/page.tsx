import type { Metadata } from "next";
import { EnquiryForm } from "@/components/marketing/enquiry-form";
import { FormPanel, PageHero } from "@/components/marketing/page-hero";
export const metadata: Metadata = { title: "Contact" };

export default function Contact() {
  return (
    <>
      <PageHero title="Contact us" intro="Questions about NetraRakshak, partnerships or data protection — write to us and the right person will reply." />
      <FormPanel><EnquiryForm kind="contact" /></FormPanel>
    </>
  );
}
