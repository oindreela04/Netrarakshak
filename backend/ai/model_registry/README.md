# Model registry

`<module>/<version>/weights.pt` + `model_card.json` (+ evaluation plots), written only by the training pipeline.
`<module>/ACTIVE` contains the version served to the application.

The registry ships EMPTY. No pretrained or synthetic model is included, so until you train a model on
licensed data the application reports "AI MODEL NOT AVAILABLE — HUMAN REVIEW REQUIRED" and every case is
graded by the ophthalmologist. Weights are excluded from git; store them in your model artefact store.
