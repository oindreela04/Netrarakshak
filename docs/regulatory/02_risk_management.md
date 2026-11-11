# Risk management — preliminary hazard analysis (ISO 14971 style, draft)

Severity S: 1 negligible … 5 catastrophic. Probability P: 1 improbable … 5 frequent (pre-control estimates; to be
re-estimated with validation data). Residual risk to be re-evaluated after verification.

| ID | Hazard / failure | Harm | S | P | Risk controls implemented | Verification |
|---|---|---|---|---|---|---|
| R1 | AI under-grades referable DR (false negative) | Delayed treatment, vision loss | 4 | 3 | Mandatory ophthalmologist review & signature; uncertainty → INCONCLUSIVE; referable-suggested cases prioritised; model gated on held-out metrics | test_review_report, test_ai_inference::uncertainty |
| R2 | AI output treated as diagnosis | Inappropriate care | 4 | 3 | "AI suggests" wording; unsigned reports watermarked DRAFT; report status derived only from signed review | test_review_report |
| R3 | Poor-quality image analysed | Wrong result | 4 | 3 | Ten-check IQA gate; non-acceptable images never sent to model | test_upload_quality, test_poor_quality… |
| R4 | Non-fundus / phone image uploaded | Meaningless result | 3 | 2 | Fundus plausibility + retinal visibility checks; magic-byte validation | test_quality_unit_cases |
| R5 | Untrained / synthetic / tampered model used | Meaningless result | 5 | 2 | Registry gate: weights SHA-256 vs card, held-out metrics required, synthetic models blocked; production refuses ALLOW flag | test_synthetic_model_blocked, test_tampered_weights_blocked |
| R6 | Wrong patient / eye association | Wrong report | 4 | 2 | Eye-specific upload slots, patient header on every screen, laterality on report, replaced images retained | UI review, test_upload_formats_and_replacement |
| R7 | Grad-CAM read as lesion map | Misinterpretation | 3 | 3 | Persistent on-image disclaimer; report caption | UI/report inspection |
| R8 | Cross-hospital data access | Privacy breach | 4 | 2 | Tenant scoping in every query; 404 on foreign IDs; super-admin has no PHI access | test_isolation |
| R9 | Unauthorised access / account takeover | Privacy breach, false sign-off | 4 | 3 | bcrypt, lockout, revocable sessions, password re-entry to sign, audit | test_auth_permissions |
| R10 | Data loss | Lost records | 3 | 2 | Backups, restore script, managed DB PITR | Restore drill (pending) |
| R11 | Distribution shift (new camera / population) | Degraded accuracy | 4 | 4 | Per-camera calibration plan; clinician-AI agreement analytics; post-market monitoring | Clinical validation plan |
| R12 | Model update changes behaviour silently | Unexpected errors | 4 | 2 | Versioned registry, version on every result and report; ACP to be filed | Pending ACP |
| R13 | AI analysis without consent | Legal/ethical harm | 3 | 2 | Consent gate in analysis; screening requires screening consent | test_poor_quality_and_missing_consent… |
