import type { Metadata } from "next";
import { PageHero, Prose } from "@/components/marketing/page-hero";
export const metadata: Metadata = { title: "Security & privacy" };

export default function Security() {
  return (
    <>
      <PageHero title="Security and privacy" intro="Retinal images are health data. NetraRakshak is designed so that each hospital controls its own records and every access is accountable." />
      <Prose>
        <h2>Isolation between hospitals</h2>
        <p>Every patient, image, AI result, review and report belongs to exactly one hospital account. Every request is scoped to the
          signed-in user&apos;s hospital on the server, and records belonging to another hospital are indistinguishable from records that do not exist.
          NetraRakshak platform administrators manage subscriptions and licences but have no access to patient records.</p>
        <h2>Access control</h2>
        <ul>
          <li>Five roles — hospital administrator, ophthalmologist, screening technician, receptionist and platform administrator — each with least-privilege permissions.</li>
          <li>Passwords hashed with bcrypt, a strong password policy, account lockout after repeated failures and short-lived access tokens with rotating refresh sessions.</li>
          <li>Users can see and revoke their active sessions. Deactivating a user ends all their sessions immediately.</li>
          <li>Report signing requires the ophthalmologist to re-enter their password and attest that they reviewed the case.</li>
        </ul>
        <h2>Encryption</h2>
        <p>All traffic is served over TLS. Retinal images, explainability maps, logos and reports are encrypted by the application before
          they are written to private object storage, and the bucket additionally applies server-side encryption. Production databases use
          encrypted managed PostgreSQL in an Indian region.</p>
        <h2>Audit trail</h2>
        <p>Logins, patient views, uploads, image views, AI runs, review decisions, signatures and report downloads are recorded with the user,
          time and IP address. Each entry is chained to the previous one with a SHA-256 hash, so alteration of the log is detectable.</p>
        <h2>Consent, retention and erasure</h2>
        <p>Consent is recorded separately for screening, AI analysis, data storage and research, and can be withdrawn. AI analysis does not
          run without AI consent. Hospitals set their retention period; erasure overwrites and deletes stored images and reports and is itself logged.</p>
        <h2>Indian regulatory context</h2>
        <p>The platform is designed with the Digital Personal Data Protection Act, 2023 and the CDSCO Medical Devices Rules, 2017 in mind.
          Design intent is not certification: NetraRakshak has not yet been assessed or approved by any regulator, and hospitals remain
          data fiduciaries for their patients&apos; records.</p>
      </Prose>
    </>
  );
}
