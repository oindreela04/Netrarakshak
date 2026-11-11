# NetraRakshak — System architecture

## Components

```
 Browser (Next.js 15, TypeScript, Tailwind, shadcn-style UI, Recharts)      Fundus camera PC
   │  public site · /login · /app/* (role-aware)                              │ capture agent (tools/capture_agent.py)
   │  HTTPS, bearer access token (30 min) + rotating refresh session          │ folder-watch / vendor SDK / DICOM
   ▼                                                                          ▼
 FastAPI (backend/app) ──────────────────────────────────────────────────────────────────────
   routers: auth · public · patients · screenings · reviews · reports · analytics · admin · platform · ai
   deps: authentication → RBAC permission check → tenant scope (hospital_id) → licence check
   services: quality (OpenCV IQA) · analysis (gate → registry → inference) · report_pdf (ReportLab) · billing
   audit: append-only, SHA-256 hash chain
   │                         │                                   │
   ▼                         ▼                                   ▼
 PostgreSQL              Private S3-compatible bucket         AI layer (backend/ai)
 (SQLite for dev only)   Fernet-encrypted objects + SSE        registry · per-disease modules · Grad-CAM
```

## Request pipeline

1. `get_current_user` validates the JWT, then checks the server-side session row (revocable) and that the user and hospital are active.
2. `require(perm)` checks the role → permission matrix in `app/security.py`.
3. `tenant_id(cu)` returns the user's hospital; super-admins have none and therefore cannot read PHI.
4. `get_owned(model, id, hospital_id)` fetches rows and returns **404** for other tenants' rows (no existence leak). Every list query filters on `hospital_id`.
5. Mutations write an audit entry (who, what, entity, IP, details without PHI values).

## Screening state machine

`draft` → (both eyes uploaded) `quality_checked` → (AI step run) `analysed` → (draft review saved) `in_review`
→ (signed with password + attestation) `signed` → (approved report generated) `reported`.
`recapture_requested` can be set from review; new uploads return the session to `draft/quality_checked`.
Signed sessions are locked against new images and review edits.

## AI analysis gate (`services/analysis.py`)

For each current image: consent for AI analysis? → quality verdict `acceptable`? → active model available in the
registry (weights hash matches card, held-out metrics present, not synthetic)? → real forward pass → uncertainty
check (confidence and normalised entropy thresholds) → Grad-CAM overlay & heatmap stored encrypted. Any failed gate
stores an `AIResult` with a non-`completed` status and the display verdict
`INCONCLUSIVE — HUMAN REVIEW REQUIRED` (or `AI MODEL NOT AVAILABLE — HUMAN REVIEW REQUIRED`). AI results are
immutable; clinician interpretation lives in `ClinicalReview`.

## Data model (main tables)

`plans`, `hospitals`, `branches`, `users`, `user_sessions`, `patients`, `consent_records`, `screenings`,
`retinal_images` (replaced images kept with `is_current=false`), `ai_results`, `clinical_reviews`, `reports`
(PDF stored encrypted, SHA-256 recorded), `audit_logs`, `demo_requests`, `invoices`.

## Camera integration

`tools/capture_agent.py` defines a `CaptureSource` interface with a working folder-watch implementation.
Further sources plug into the same interface:

| Source | Mechanism | Notes |
|---|---|---|
| Folder export | Camera software exports JPEG/TIFF to a folder | Works with most desktop fundus cameras today |
| DICOM | C-STORE SCP or DICOMweb STOW-RS receiving Ophthalmic Photography (OP) objects | Map PatientID/AccessionNumber to screening; strip burned-in PHI |
| Vendor SDK | Manufacturer's documented SDK on the capture PC | Requires the vendor's SDK licence and documentation; not bundled |

Uploads carry `source=camera_agent`; quality checks run server-side. An ordinary phone camera is not a fundus
camera and is not supported; non-fundus images fail the fundus-plausibility and retinal-visibility checks.

## Disease modules

`ai/registry.py` declares each module (DR implemented; glaucoma, AMD, hypertensive retinopathy and other
abnormalities declared but not activated). Each module has its own folder, data, model card and activation, and
would produce its own `AIResult` rows. No generic "detect everything" model exists.
