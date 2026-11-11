# Clinical validation plan (draft protocol outline)

**Not started.** No clinical validation has been performed.

1. **Objective.** Estimate sensitivity and specificity of NetraRakshak's AI suggestion for referable DR (moderate NPDR
   or worse, and/or DME) against a reference standard, in the intended Indian screening population, and evaluate the
   clinician-in-the-loop workflow.
2. **Design.** Prospective, multi-centre (≥3 sites, ≥2 camera makes), consecutive enrolment of adults with diabetes;
   images captured per site protocol; AI run blinded to graders.
3. **Reference standard.** Independent grading by two certified graders with adjudication by a retina specialist
   (ICDR + DME); optional dilated clinical exam subset.
4. **Primary endpoints.** Sensitivity and specificity for referable DR with 95% CIs; pre-specified thresholds (e.g.
   sensitivity lower CI bound ≥ 85%, specificity ≥ 80% — to be agreed with clinical advisors/regulator).
5. **Secondary.** Gradability rate; inconclusive rate; per-grade agreement (quadratic weighted kappa); calibration;
   subgroup performance (age, sex, camera, dilation, site); time to report; clinician–AI agreement.
6. **Sample size.** Driven by referable-DR prevalence (~10–20% in screening populations) and precision targets;
   typically 1,500–3,000 participants to obtain ≥200 referable cases. Finalise with a statistician.
7. **Ethics & registration.** Institutional ethics committee approval at each site, CTRI registration, written
   informed consent (local language), DPDP-compliant data handling.
8. **Regulatory.** Confirm with CDSCO whether a test licence / clinical investigation permission is required for the
   applicable class before enrolment.
9. **Locked model.** A single frozen model version (weights SHA-256 recorded) is used throughout.
