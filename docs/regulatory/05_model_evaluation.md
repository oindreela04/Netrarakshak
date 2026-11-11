# Model evaluation documentation

## Current status — model NR-DR-efficientnet_b0 v2026.11.11-1219 (ACTIVE)
Trained 11 Nov 2026 on a Kaggle GPU by the product owner's account with `tools/kaggle_notebook_train.py`.
Weights SHA-256 verified against the model card at installation. **Not clinically validated.**

| Item | Value |
|---|---|
| Data | APTOS 2019 Blindness Detection (Kaggle), 3,662 images; competition rules accepted by the account holder; **commercial use not confirmed** |
| Split | train 2,615 / validation 523 / test 524, grade-stratified |
| Architecture | EfficientNet-B0, ImageNet initialisation, 384 px, Ben Graham preprocessing |
| Training | 14 epochs (early stopped), best epoch 8, validation QWK 0.887; temperature T = 0.771 |

Held-out test set (n = 524), computed by the pipeline:

| Metric | Value |
|---|---|
| Accuracy | 81.9% |
| Quadratic weighted kappa | 0.876 |
| Macro precision / recall / F1 | 68.0% / 67.8% / 67.0% |
| Weighted F1 | 82.1% |
| Macro ROC-AUC (one-vs-rest) | 0.917 |
| **Referable DR (≥ moderate NPDR)** sensitivity / specificity | **82.0% (168/205) / 96.6% (308/319)** |
| Referable DR PPV / NPV / ROC-AUC | 93.9% / 89.3% / 0.981 |
| Expected calibration error before → after temperature scaling | 12.2% → 6.1% |

Per class (sensitivity / precision): no apparent DR 99.3% / 97.1%; mild 71.7% / 50.0%; moderate 64.7% / 76.1%;
severe 44.0% / 34.4%; proliferative 59.6% / 82.4%.

Confusion matrix (rows reference, columns predicted; No, Mild, Moderate, Severe, PDR):
`[[271,1,0,0,1],[3,33,9,0,1],[4,26,86,15,2],[0,0,12,11,2],[1,6,6,6,28]]`

### Interpretation and limitations
- At the argmax operating point **37 of 205 referable eyes (18%) were graded non-referable**, mostly moderate → mild.
  This is why every case requires ophthalmologist review; the model must not be used to rule out disease.
- Severe NPDR and PDR are weak (small classes, 25 and 47 test images).
- APTOS publishes no patient IDs, so splitting was image-level; both eyes of one person may fall in different
  splits, which can make these figures optimistic.
- Single-source data (one Indian hospital network, specific cameras); external validation (e.g. IDRiD, Messidor-2,
  partner-hospital data) has not been done.
- **Out-of-distribution behaviour:** on procedurally generated synthetic test images the model gave confident grades
  (e.g. 92.7% "Mild NPDR"). The quality gate checks image properties, not whether the content is a real retina it
  can grade, so an unusual image can still receive a confident output. An OOD detector is a priority improvement.
- Uncertainty thresholds are still the defaults (confidence < 0.60 or entropy > 0.75); tune them on validation
  predictions to route more borderline moderate/mild cases to INCONCLUSIVE.

### Verification of the synthetic smoke-test path
Automated tests separately train a throwaway model on synthetic images to exercise the code path; such models are
blocked from patient use by the registry and their metrics are not reported.

## Evaluation procedure (implemented in `ai/modules/diabetic_retinopathy/train.py`)
- Patient-grouped, grade-stratified 70/15/15 split (StratifiedGroupKFold); split files saved with the run.
- Model selection on validation quadratic weighted kappa; early stopping.
- Temperature scaling fitted on the validation set only.
- Test-set metrics computed once on the held-out split and written to `model_card.json`:
  accuracy; per-class precision, recall (sensitivity), specificity, F1, one-vs-rest ROC-AUC; macro/weighted F1;
  macro ROC-AUC; quadratic weighted kappa; confusion matrix; referable-DR (≥ moderate) sensitivity, specificity,
  PPV, NPV, ROC-AUC; expected calibration error before/after calibration; ROC and confusion-matrix plots.
- External evaluation on other datasets: `evaluate.py` appends to `external_evaluations.json`.

## Uncertainty thresholds
Defaults: confidence < 0.60 or normalised entropy > 0.75 → INCONCLUSIVE. These must be re-tuned on validation data
for the chosen operating point (e.g. to cap the false-negative rate among non-inconclusive cases) and documented here.

## Image-quality thresholds
Heuristic defaults in `services/quality.py` must be calibrated against clinician gradability labels per camera model
(e.g. using EyeQ-style labels), reporting agreement (Cohen's kappa) with human gradability judgements.
