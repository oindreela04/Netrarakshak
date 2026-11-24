"""Inference adapter for the multi-disease fundus model (ODIR-5K, 8 multi-label categories).

Each category has its own sigmoid probability and a decision threshold chosen on the validation set by the
training script. A category is "flagged" when its probability reaches its threshold. The Grad-CAM map is drawn for
the most probable flagged abnormality (or for "normal" when nothing abnormal is flagged).
"""
import json
import threading
import time
from pathlib import Path

import cv2
import numpy as np
import torch

from ai.common.gradcam import overlay
from ai.common.preprocess import crop_to_retina, pad_square, preprocess_bgr, to_tensor
from ai.modules.diabetic_retinopathy.model import build_model

NO_FINDING = "NO CATEGORY ABOVE THRESHOLD — HUMAN REVIEW REQUIRED"


class MultiDiseasePredictor:
    def __init__(self, version_dir: Path):
        self.card = json.loads((version_dir / "model_card.json").read_text())
        self.arch = self.card["architecture"]
        self.size = int(self.card["input_size"])
        self.keys = self.card["class_keys"]
        self.names = self.card["class_names"]
        self.thr = np.array([float(self.card["thresholds"][k]) for k in self.keys], np.float32)
        self.model = build_model(self.arch, num_classes=len(self.keys), pretrained=False)
        self.model.load_state_dict(torch.load(version_dir / "weights.pt", map_location="cpu", weights_only=True))
        self.model.eval()
        self.lock = threading.Lock()

    def predict(self, bgr: np.ndarray) -> dict:
        t0 = time.perf_counter()
        x = to_tensor(preprocess_bgr(bgr, self.size)).unsqueeze(0)
        with self.lock, torch.inference_mode():
            feats = self.model.features(x)
            logits = self.model.classifier(torch.flatten(self.model.avgpool(feats), 1))[0]
            probs = torch.sigmoid(logits).numpy()
            flagged = [i for i in np.argsort(-probs) if probs[i] >= self.thr[i]]
            abnormal = [i for i in flagged if self.keys[i] != "normal"]
            target = abnormal[0] if abnormal else (flagged[0] if flagged else int(np.argmax(probs)))
            w = self.model.classifier[-1].weight[target]
            cam = torch.relu((w[:, None, None] * feats[0]).sum(0)).numpy().astype(np.float32)
        if cam.max() > 0:
            cam = cam / cam.max()
        disp = cv2.cvtColor(cv2.resize(pad_square(crop_to_retina(bgr)), (512, 512), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2RGB)
        over, heat = overlay(disp, cam)
        if abnormal:
            verdict = "AI flags: " + ", ".join(self.names[i] for i in abnormal)
            expl = ("Categories at or above their validated thresholds: "
                    + "; ".join(f"{self.names[i]} {probs[i]:.0%} (threshold {self.thr[i]:.0%})" for i in abnormal)
                    + ". Screening flags only, not diagnoses; requires clinician confirmation.")
        elif flagged:
            verdict = f"AI suggests: {self.names[flagged[0]]}"
            expl = "No abnormal category reached its threshold. Requires clinician confirmation."
        else:
            verdict = NO_FINDING
            expl = "No category reached its decision threshold, so the model makes no suggestion."
        return {
            "predicted_index": int(target), "predicted_label": self.names[target],
            "probabilities": {k: round(float(p), 6) for k, p in zip(self.keys, probs)},
            "flagged": [self.keys[i] for i in flagged], "confidence": float(probs[target]),
            "is_uncertain": not flagged, "display_verdict": verdict, "explanation": expl,
            "overlay_rgb": over, "heatmap_rgb": heat, "inference_ms": int((time.perf_counter() - t0) * 1000),
            "model_name": self.card["model_name"], "model_version": self.card["version"],
            "thresholds": {k: float(t) for k, t in zip(self.keys, self.thr)},
        }
