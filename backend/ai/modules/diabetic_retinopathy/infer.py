"""Inference adapter: real forward pass of the registered DR model on an uploaded photograph."""
import json
import time
from pathlib import Path

import cv2
import numpy as np
import torch

from ai.common.gradcam import GradCAM, overlay
from ai.common.preprocess import crop_to_retina, pad_square, preprocess_bgr, to_tensor
from ai.modules.diabetic_retinopathy.model import build_model, gradcam_layer

INCONCLUSIVE = "INCONCLUSIVE — HUMAN REVIEW REQUIRED"


class DRPredictor:
    def __init__(self, version_dir: Path):
        self.card = json.loads((version_dir / "model_card.json").read_text())
        self.arch = self.card["architecture"]
        self.size = int(self.card["input_size"])
        self.T = float(self.card.get("temperature", 1.0))
        self.class_names = self.card["class_names"]
        self.class_keys = self.card["class_keys"]
        self.model = build_model(self.arch, num_classes=len(self.class_names), pretrained=False)
        self.model.load_state_dict(torch.load(version_dir / "weights.pt", map_location="cpu", weights_only=True))
        self.model.eval()
        self.lock = __import__("threading").Lock()

    def predict(self, bgr: np.ndarray, conf_thr: float, entropy_thr: float) -> dict:
        t0 = time.perf_counter()
        rgb = preprocess_bgr(bgr, self.size)
        x = to_tensor(rgb).unsqueeze(0)
        with self.lock:
            if self.arch.startswith("efficientnet"):
                # EfficientNet ends in global average pooling + one linear layer, so the Grad-CAM channel weights
                # equal the classifier weights for the predicted class (up to the constant 1/(H*W), removed by the
                # max-normalisation). Computing the map this way needs no backward pass and no autograd graph,
                # which keeps peak memory low enough for a 512 MB server; the map is identical to GradCAM's.
                with torch.inference_mode():
                    feats = self.model.features(x)
                    logits = self.model.classifier(torch.flatten(self.model.avgpool(feats), 1))[0]
                    probs = torch.softmax(logits / self.T, 0).numpy()
                    idx = int(probs.argmax())
                    w = self.model.classifier[-1].weight[idx]
                    cam = torch.relu((w[:, None, None] * feats[0]).sum(0)).numpy().astype(np.float32)
                if cam.max() > 0:
                    cam = cam / cam.max()
            else:
                with torch.no_grad():
                    logits = self.model(x)[0]
                probs = torch.softmax(logits / self.T, 0).numpy()
                idx = int(probs.argmax())
                cam_tool = GradCAM(self.model, gradcam_layer(self.model, self.arch))
                try:
                    cam = cam_tool(x, idx)
                finally:
                    cam_tool.remove()
        conf = float(probs[idx])
        ent = float(-(probs * np.log(probs + 1e-12)).sum() / np.log(len(probs)))
        reasons = []
        if conf < conf_thr:
            reasons.append(f"top-class confidence {conf:.0%} is below the {conf_thr:.0%} threshold")
        if ent > entropy_thr:
            reasons.append(f"prediction entropy {ent:.2f} exceeds {entropy_thr:.2f}")
        uncertain = bool(reasons)

        # explainability images at display resolution, on the un-normalised (cropped) photograph
        disp = cv2.cvtColor(cv2.resize(pad_square(crop_to_retina(bgr)), (512, 512), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2RGB)
        over, heat = overlay(disp, cam)
        return {
            "predicted_index": idx, "predicted_key": self.class_keys[idx], "predicted_label": self.class_names[idx],
            "probabilities": {k: round(float(p), 6) for k, p in zip(self.class_keys, probs)},
            "confidence": conf, "normalized_entropy": ent, "is_uncertain": uncertain,
            "display_verdict": INCONCLUSIVE if uncertain else f"AI suggests: {self.class_names[idx]}",
            "explanation": ("Model is uncertain: " + "; ".join(reasons) + ".") if uncertain else
                           "Model output above the configured certainty thresholds. Requires clinician confirmation.",
            "overlay_rgb": over, "heatmap_rgb": heat, "inference_ms": int((time.perf_counter() - t0) * 1000),
            "model_name": self.card["model_name"], "model_version": self.card["version"],
        }
