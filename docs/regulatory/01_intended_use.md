# Intended use and indications (draft)

**Intended use.** NetraRakshak is software intended to assist qualified ophthalmologists in screening colour fundus
photographs of adults with diabetes for signs of diabetic retinopathy, by (a) assessing image quality, (b) providing
an AI-generated suggested ICDR grade with calibrated confidence and an explainability map, and (c) structuring the
clinician's review and report. All outputs are reviewed, and accepted, modified or rejected by an ophthalmologist
before a report is issued.

**Intended users.** Screening technicians (image capture/upload), receptionists (registration, consent),
ophthalmologists (interpretation, sign-off), hospital administrators.

**Intended environment.** Hospitals, eye clinics and diagnostic centres in India using compatible colour fundus cameras.

**Patient population.** Adults (≥18 y) with diabetes mellitus undergoing retinal screening.

**Not intended for:** autonomous diagnosis; use without ophthalmologist review; emergency triage; paediatric
patients; detection of glaucoma, AMD, hypertensive retinopathy, retinal detachment, tumours or other conditions
(modules inactive); diagnosis of stroke, cataract, cardiovascular or systemic disease; images from smartphone
cameras or non-fundus devices; assessment of diabetic macular oedema by the AI (the clinician may record it).

**Contraindications / limitations.** Media opacity, small pupils and poor fixation reduce gradability; ungradable
images are rejected. AI performance on cameras/populations not represented in training data is unknown until
validated.
