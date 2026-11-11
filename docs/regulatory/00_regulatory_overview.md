# Regulatory readiness overview (India)

Status: **pre-regulatory, investigational**. NetraRakshak has not been classified, licensed, certified or clinically
validated. Nothing in this repository claims compliance; these documents are working drafts to prepare for assessment.

## Applicable framework (as understood November 2026 — confirm with a regulatory consultant)

| Instrument | Relevance |
|---|---|
| Medical Devices Rules, 2017 (MDR 2017) under the Drugs and Cosmetics Act, 1940 | Software intended for diagnosis/screening of disease is a medical device; risk classes A–D |
| CDSCO *Draft Guidance Document on Medical Device Software* (21 Oct 2025, consultation concluded; draft at last check) | Classifies standalone software by significance of information and seriousness of the condition (IMDRF-style); requires lifecycle QMS, risk management, clinical evaluation, V&V documentation; introduces an **Algorithm Change Protocol (ACP)** for AI model updates; post-market surveillance incl. cybersecurity vulnerability reporting |
| Digital Personal Data Protection Act, 2023 and DPDP Rules | Health data of patients; hospitals are data fiduciaries, NetraRakshak a data processor; consent, purpose limitation, security safeguards, breach notification, erasure |
| ABDM / ABHA guidelines | Optional ABHA ID capture; integration would require ABDM sandbox certification |
| ICMR Ethical Guidelines for AI in Healthcare (2023) / clinical research guidelines | Clinical validation study design, ethics committee approval, CTRI registration |

## Expected classification (to be confirmed)
A DR screening aid that informs a clinician's decision for a serious but non-immediately-life-threatening
condition is likely **Class B or C** under the draft guidance; autonomous diagnosis would push higher. The initial
release is designed as **clinician-supervised** (every report requires an ophthalmologist's signature) to stay at
the lower end. Classification must be confirmed with CDSCO / a notified body.

## Standards gap assessment

| Standard | Purpose | Current state | Gap |
|---|---|---|---|
| ISO 13485:2016 | QMS for medical devices | No certified QMS | Establish QMS (document control, CAPA, supplier control, design controls) |
| IEC 62304:2006+A1:2015 | Software lifecycle | Code, tests, requirements and architecture exist; no formal SDP/SOUP list/problem resolution process | Software development plan, SOUP register (FastAPI, PyTorch, Next.js…), traceability matrix, release process; likely software safety class B |
| ISO 14971:2019 | Risk management | Initial hazard analysis in `02_risk_management.md` | Risk management plan, file, benefit-risk, post-production feedback |
| IEC 62366-1:2015 | Usability engineering | Workflow designed for non-technical staff | Use specification, formative/summative usability studies |
| IEC 81001-5-1:2021 | Health software security lifecycle | Controls in `07_cybersecurity.md` | Threat model sign-off, pen test, SBOM, vulnerability handling process |
| ISO/IEC 27001 | Information security management | — | Recommended for enterprise sales |
| IMDRF GMLP principles / ISO/IEC 42001 | AI lifecycle | Model cards, held-out evaluation, gating, ACP-ready registry | Data management plan, bias analysis, ACP document |

## Document index
01 Intended use · 02 Risk management · 03 Software requirements · 04 Clinical validation plan ·
05 Model evaluation · 06 Dataset documentation · 07 Cybersecurity · 08 Technical documentation ·
09 User manual · 10 Verification & validation records
