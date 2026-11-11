# Module: amd — NOT ACTIVATED

This module is registered in `ai/registry.py` with `implemented=False`. It is deliberately inactive:
no model has been trained or validated, so the platform never produces a amd finding.

To implement it, follow the same contract as `ai/modules/diabetic_retinopathy/`:

1. `dataset.py` — loader for appropriately licensed, clinician-labelled data with patient-grouped splits.
2. `model.py` — architecture and Grad-CAM target layer (segmentation-based designs are preferred for
   glaucoma: optic disc/cup segmentation → vertical cup-to-disc ratio).
3. `train.py` — training, calibration on validation data, held-out test metrics, model card written to
   `ai/model_registry/amd/<version>/`.
4. `infer.py` — predictor returning probabilities, uncertainty and explainability maps.
5. Add the adapter in `registry.get_predictor`, set `implemented=True`, extend `services/analysis.py` to run
   it as an independent result row, and add its section to the clinician review form and PDF.
6. Complete the module's risk analysis, clinical validation and regulatory update before activation.

See `registry.MODULES["amd"]` for data requirements, candidate datasets and scope limits.
