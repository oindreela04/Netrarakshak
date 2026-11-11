import type { Metadata } from "next";
import Link from "next/link";
import { PageHero, Prose } from "@/components/marketing/page-hero";
import { Button } from "@/components/ui/button";
export const metadata: Metadata = { title: "Hospital solutions" };

export default function Solutions() {
  return (
    <>
      <PageHero title="Screening programmes that fit your hospital" intro="From one fundus camera in a clinic to diabetic retinopathy screening across a network of branches." />
      <Prose>
        <h2>Diabetes outpatient screening</h2>
        <p>Photograph patients in the diabetes OPD, check image quality on the spot, and send gradable cases to the ophthalmology queue
          the same day. Referable and uncertain cases are sorted to the top of the queue.</p>
        <h2>Eye clinics</h2>
        <p>A complete patient record, screening history and branded reports without installing servers. Bring your existing fundus camera.</p>
        <h2>Hospital networks</h2>
        <p>Run every branch from one account with central analytics, per-branch teams and a single audit trail. Enterprise plans include
          dedicated hosting in an Indian region and single sign-on.</p>
        <h2>Teams and roles</h2>
        <ul>
          <li><strong>Receptionists</strong> register patients and record consent.</li>
          <li><strong>Technicians</strong> capture and upload images and act on quality feedback.</li>
          <li><strong>Ophthalmologists</strong> review, grade, refer and sign.</li>
          <li><strong>Administrators</strong> manage the team, branches, branding, subscription and audit trail.</li>
        </ul>
        <div className="pt-4"><Button asChild variant="primary" className="rounded-full px-5"><Link href="/request-demo">Plan a pilot with us</Link></Button></div>
      </Prose>
    </>
  );
}
