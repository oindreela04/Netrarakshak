# Module: diabetic_retinopathy

Five-grade ICDR classifier (no apparent DR, mild, moderate, severe NPDR, proliferative DR).

| File | Purpose |
|---|---|
| `dataset.py` | APTOS / EyePACS / generic CSV loaders, patient-grouped stratified split, augmentation, imbalance handling |
| `model.py` | EfficientNet-B0/B3 or ResNet-50 backbone (ImageNet init) + 5-class head; Grad-CAM layer |
| `train.py` | Training, early stopping on validation QWK, temperature calibration, held-out test metrics, plots, model card, registry |
| `evaluate.py` | External evaluation of a registered version on another labelled dataset |
| `infer.py` | Production predictor: preprocessing, calibrated probabilities, uncertainty, Grad-CAM overlay/heatmap |

## Training on Windows

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m ai.modules.diabetic_retinopathy.train `
  --labels D:\datasets\aptos2019\train.csv --images D:\datasets\aptos2019\train_images `
  --dataset-name "APTOS 2019" --dataset-licence "<the terms you accepted>" `
  --arch efficientnet_b0 --size 384 --epochs 25 --batch-size 16 --workers 4
```

A CUDA GPU is strongly recommended (CPU training of 3,662 APTOS images at 384 px takes many hours per epoch).
The trained version is copied to `ai/model_registry/diabetic_retinopathy/<version>/` and made ACTIVE.
Restart the API to load it. Metrics shown in the app come only from the model card this script writes.
