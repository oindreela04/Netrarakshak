# Datasets — licensing and suitability

**No dataset is bundled with NetraRakshak and no model has been trained on real data in this repository.**
Before training, the product owner must obtain each dataset from its official source, read and accept its terms,
and record those terms in the training command (`--dataset-licence`). The model card then carries them.

| Dataset | Content | Terms (verify at source) | Suitability for a commercial product |
|---|---|---|---|
| APTOS 2019 Blindness Detection (Kaggle) | ~3,662 labelled fundus images, ICDR 0–4, Aravind Eye Hospital (India) | Kaggle competition rules; redistribution and use outside the competition may be restricted | Valuable (Indian population) but **commercial use must be confirmed with Kaggle/APTOS before relying on it**. Suitable for research/prototyping only until cleared. |
| EyePACS / Kaggle DR Detection 2015 | ~35k training images, ICDR 0–4, US screening programme | Kaggle competition terms; mirrors describe use as restricted under Kaggle & EyePACS terms | Same caution; licensing from EyePACS directly is the route for commercial use. |
| IDRiD | 516 images with DR/DME grades, India | CC BY 4.0 (check current page) | Good external test set; small. |
| Messidor-2 | 1,748 images | Licence on request; research terms | Common external benchmark; confirm commercial terms. |
| DDR | 13,673 images, China | Research use | Research only unless licensed. |
| RFMiD | Multi-disease, India | CC BY 4.0 (check) | Candidate for the "other abnormalities" triage module. |
| Partner hospital data | Prospective Indian data | Data-sharing agreement + ethics approval + DPDP-compliant consent | **Required** for clinical validation and the strongest training basis for a commercial product. |

Recommended path: prototype on public data where permitted → sign data agreements with 2–3 Indian hospital partners
(multiple camera makes, dilated and undilated) → train on licensed/partner data → external test on IDRiD and a
held-out partner site → prospective clinical validation (see `regulatory/04_clinical_validation_plan.md`).

Labelling standard: ICDR grade per image by ≥2 certified graders with adjudication by a retina specialist;
record gradability, DME presence and camera model as metadata.
