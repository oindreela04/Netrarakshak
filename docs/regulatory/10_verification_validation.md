# Verification and validation records

## Verification (automated) — run 11 Nov 2026, build 0.9.0
Command: `python -m pytest -q` (backend). Result: **30 passed**.

| Suite | Tests | Covers |
|---|---|---|
| test_auth_permissions.py | 10 | login, generic errors, lockout, refresh rotation, logout revocation, password policy, role permissions, super-admin PHI isolation, plan user limit |
| test_isolation.py | 1 (13 assertions) | cross-tenant read/write/list/audit isolation for patients, screenings, images, reports |
| test_patients.py | 4 | registration, search/filter, edit, archive/restore, consent gate, permanent erasure |
| test_upload_quality.py | 3 | IQA verdicts (good, blurred, dark, low-res, non-fundus), JPEG/PNG/TIFF, replacement history, rejection of bad files, encryption at rest |
| test_ai_inference.py | 7 | model-unavailable routing, synthetic-model blocking, real forward pass + Grad-CAM, determinism, uncertainty → INCONCLUSIVE, quality/consent gates, tamper detection, computed model-card metrics |
| test_review_report.py | 5 | review validation, signing (attestation/password), locking, draft vs approved PDF, patient history, dashboard update, recapture, audit chain, billing/licence suspension, public enquiry |

Frontend: `tsc --noEmit` clean; `next build` succeeds (25 routes).

End-to-end (browser, Playwright, synthetic data): admin login → technician registers patient → uploads right and
left synthetic fundus images → quality acceptable → AI step run (no model active → "AI MODEL NOT AVAILABLE — HUMAN
REVIEW REQUIRED") → ophthalmologist grades, refers and signs → signed PDF generated → patient history and dashboard
updated. Separately, the completed-AI UI path (probabilities, Grad-CAM overlay, compare view) was exercised against a
synthetic smoke-test model in an isolated scratch environment with loosened thresholds — not shipped.

## Installation verification of model v2026.11.11-1219 (11 Nov 2026)
Weights SHA-256 matched the model card; registry reported the module available; weights loaded with
`weights_only=True`; CPU inference ≈ 0.3–0.7 s per eye including Grad-CAM. Browser E2E repeated with the model
active: AI grades, calibrated probabilities and Grad-CAM overlays displayed; clinician accepted (OD) and modified (OS)
the AI suggestions; signed report generated. 30 automated tests pass.

## Validation
**Not performed.** Synthetic test data verifies software behaviour only and says nothing about clinical performance.
