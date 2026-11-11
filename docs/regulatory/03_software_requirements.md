# Software requirements specification (summary, draft)

| ID | Requirement | Implemented in | Verified by |
|---|---|---|---|
| SR-01 | Register patients with unique hospital-scoped ID, demographics, diabetes/hypertension history, medications | `routers/patients.py`, `/app/patients/new` | test_register_search_edit_archive |
| SR-02 | Search, filter, edit, archive, restore, permanently erase patients | patients router | test_patients |
| SR-03 | Record, view and withdraw consent per purpose; block screening without screening consent | patients/screenings routers | test_screening_requires_consent |
| SR-04 | Upload right/left JPEG/JPG/PNG/TIFF by drag-and-drop; replace; record metadata & SHA-256 | screenings router, `EyeDrop` | test_upload_formats_and_replacement |
| SR-05 | Encrypt stored images and reports | `storage.py` | test_images_are_encrypted_at_rest |
| SR-06 | Automatic quality assessment with verdict and reasons before AI | `services/quality.py` | test_quality_unit_cases |
| SR-07 | Run AI only on acceptable images with consent and an available validated model | `services/analysis.py` | test_ai_inference |
| SR-08 | Report calibrated probabilities, confidence, uncertainty; INCONCLUSIVE when uncertain | `infer.py` | test_uncertainty_forces_inconclusive |
| SR-09 | Grad-CAM overlay and heatmap labelled as explainability | `gradcam.py`, viewer | test_real_inference_and_gradcam |
| SR-10 | Viewer: zoom, pan, fit, overlay/heatmap, OD+OS side-by-side, compare | `retinal-viewer.tsx` | E2E screenshots |
| SR-11 | Clinician review: accept/modify/reject per eye, observations, referral, recapture, sign with password | reviews router, `/app/review/[id]` | test_review_sign_and_report |
| SR-12 | AI output immutable and separate from clinician interpretation | `AIResult` vs `ClinicalReview` | code review |
| SR-13 | PDF report with all required fields; approved only after signature | `report_pdf.py` | test_review_sign_and_report |
| SR-14 | Multi-tenant isolation; 5 roles; permissions | `deps.py`, `security.py` | test_isolation, test_role_permissions |
| SR-15 | Plans, usage limits, licence status, invoices | admin/platform routers, billing | test_platform_billing, test_plan_user_limit |
| SR-16 | Tamper-evident audit trail | `audit.py` | test_audit_chain_intact |
