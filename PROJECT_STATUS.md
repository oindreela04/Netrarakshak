# PROJECT_STATUS — NetraRakshak v0.9.0

Last updated: 11 Nov 2026, 19:45 IST (realistic eye hero, deploy-ready, IEEE report). Legend: ✅ done and tested · 🟡 done, needs external input or hardening · ⛔ blocked on external input

| # | Phase | Status | Notes |
|---|---|---|---|
| 1 | Architecture & setup | ✅ | Modular FastAPI + Next.js; Windows setup/start/test scripts; env templates |
| 2 | Frontend & branding | ✅ | Light theme throughout; realistic 3D eye hero (Three.js) that blinks, follows the pointer and zooms through the pupil to the retina on scroll, scroll reveals and 3D tilt cards; reduced-motion respected. Public site (landing, technology, solutions, security, contact, demo request, login) and 18 app screens; navy/white/teal/clinical-blue system; responsive |
| 3 | Backend & database | ✅ | 15 tables via SQLAlchemy; PostgreSQL or SQLite (dev). 🟡 Alembic migrations to add before first production release |
| 4 | Authentication & permissions | ✅ | bcrypt, lockout, revocable rotating sessions, 5 roles, permission matrix. 🟡 MFA, SSO (Enterprise) not yet built |
| 5 | Patient management | ✅ | Unique IDs, full history, consent records/withdrawal, search/filter, edit, archive, erasure |
| 6 | Retinal image upload | ✅ | OD/OS drag-and-drop, JPEG/PNG/TIFF, previews, replacement with history, metadata/EXIF, SHA-256, encrypted storage, session management; camera capture agent (folder-watch). ⛔ vendor SDK/DICOM adapters need manufacturer SDKs |
| 7 | Image quality assessment | ✅ | 10 checks, Acceptable / Recapture required / Inconclusive with reasons. 🟡 thresholds are uncalibrated defaults — calibrate per camera with graded data |
| 8 | DR model training & inference | ✅ / 🟡 | **Trained model active: NR-DR-efficientnet_b0 v2026.11.11-1219** (APTOS 2019, Kaggle GPU). Held-out test: accuracy 81.9%, QWK 0.876, referable-DR sensitivity 82.0% / specificity 96.6%. 🟡 Not clinically validated; APTOS commercial terms unconfirmed; image-level split; no external validation; no out-of-distribution detection. See docs/regulatory/05_model_evaluation.md |
| 9 | Explainability | ✅ | Grad-CAM overlay + heatmap stored per result; viewer and PDF, labelled as non-findings |
| 10 | Clinician review | ✅ | Separate workspace & prioritised queue; accept/modify/reject; observations; referral; recapture; password+attestation signing; AI output kept immutable |
| 11 | PDF reporting | ✅ | Branded A4 report with all required fields; DRAFT watermark until signed; view/print/download; history |
| 12 | Multi-hospital SaaS | ✅ | Tenancy isolation, branches, branding/logo, plans (Starter/Professional/Enterprise), usage limits, licence status/expiry enforcement, GST invoices, super-admin console. 🟡 payment-gateway adapter is a stub (needs Razorpay/Stripe keys) |
| 13 | Additional disease modules | 🟡 | Glaucoma, AMD, hypertensive retinopathy, other abnormalities declared with data requirements and READMEs; deliberately **not activated** |
| 14 | Security & automated testing | ✅ | 30 backend tests passing; frontend typecheck + build; browser E2E of the full acceptance workflow. 🟡 pen test, SBOM, rate limiting, MFA |
| 15 | Deployment | 🟡 | Deploy-ready: `render.yaml` (API + AI + PostgreSQL + disk), `frontend/vercel.json`, CPU-only PyTorch requirements, Git repository with initial commit, step-by-step `docs/DEPLOY.md`. Verified in production mode on PostgreSQL with gunicorn (full E2E). Not yet deployed: needs your GitHub, Render and Vercel accounts. |

## Final acceptance test
Admin login → technician registers patient → uploads right/left images → quality checked → **trained model analyses
the photographs** (grades, calibrated confidence, Grad-CAM) → ophthalmologist accepts/modifies and signs → PDF
generated → history saved → dashboard updates: **passes end-to-end** (browser test, synthetic patient and images).

## Documentation
- IEEE-format project report: `report/netrarakshak_ieee.pdf` (LaTeX source alongside)

## What I need from you (product owner)
1. **Commercial rights to training data**: confirm APTOS terms or retrain on partner-hospital / licensed data.
2. **Real, consented fundus images** from your cameras to test the model and tune quality and uncertainty thresholds.
3. **Real, consented test images** from your target fundus cameras, plus their export formats / SDK docs.
4. Cloud accounts (Vercel, AWS/Azure/GCP in an Indian region), domain, payment gateway keys.
5. Clinical and regulatory advisors for classification, validation protocol and QMS.

## Known limitations
- Tokens are kept in sessionStorage (XSS exposure mitigated by CSP); move to httpOnly cookies behind a same-site API domain.
- Report and patient numbering use count+1 with uniqueness retry; use DB sequences under high concurrency on PostgreSQL.
- Google Fonts load at runtime; self-host fonts for offline hospital networks.
