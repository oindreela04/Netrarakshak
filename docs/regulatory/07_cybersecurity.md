# Cybersecurity documentation (draft)

| Area | Control (implemented) |
|---|---|
| Authentication | bcrypt (cost 12); password policy; lockout after 5 failures for 15 min; generic login errors; timing-equalised unknown-user path |
| Sessions | 30-min JWT access tokens bound to a server-side session; refresh rotation (single use); logout, password change, deactivation and admin reset revoke sessions; users can revoke devices; tokens in sessionStorage (cleared on tab close) |
| Authorisation | Role→permission matrix; every PHI query tenant-scoped; foreign IDs return 404; platform admins have no PHI access |
| Signing | Password re-entry + attestation; SHA-256 signature hash over review content |
| Transport | TLS at the edge; HSTS in production; CORS allow-list |
| At rest | Fernet (AES-128-CBC + HMAC-SHA256) on all stored images, maps, logos and PDFs; S3 SSE; managed DB encryption |
| Input handling | Extension + magic-byte checks, size limit, decode validation; Pydantic validation; storage-key sanitisation |
| Web | CSP, X-Frame-Options DENY, nosniff, Referrer-Policy, Permissions-Policy; images served via authenticated blob fetch, `no-store` |
| Audit | Hash-chained log of auth events, views, uploads, AI runs, reviews, signatures, reports, admin actions; verification endpoint |
| Errors | Generic 500 responses; no stack traces or PHI returned |
| Secrets | Environment variables only; production start-up refuses weak/missing secrets |
| Model integrity | Weights SHA-256 verified against model card before loading |
| Deletion | Erasure overwrites local blobs before unlinking; crypto-shredding via key rotation |

Outstanding before production: independent penetration test; SBOM (CycloneDX) and dependency scanning in CI; MFA
(TOTP) for clinicians/admins; rate limiting at the edge (WAF); key rotation procedure for STORAGE_ENCRYPTION_KEY;
incident response & CERT-In 6-hour reporting procedure; vulnerability disclosure policy; httpOnly-cookie session
option behind a same-site API domain.
