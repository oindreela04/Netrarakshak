"""Grad-CAM (Selvaraju et al., 2017) for CNN classifiers.

Grad-CAM shows which image regions most influenced the model's score for a class. It is a model
explainability aid, NOT a lesion segmentation and NOT a confirmed clinical finding.
"""
import cv2
import numpy as np
import torch


class GradCAM:
    def __init__(self, model: torch.nn.Module, target_layer: torch.nn.Module):
        self.model = model
        self.activations = None
        self.gradients = None
        self._h1 = target_layer.register_forward_hook(self._fwd)
        self._h2 = target_layer.register_full_backward_hook(self._bwd)

    def _fwd(self, _m, _i, out):
        self.activations = out.detach()

    def _bwd(self, _m, _gi, go):
        self.gradients = go[0].detach()

    def remove(self):
        self._h1.remove()
        self._h2.remove()

    def __call__(self, x: torch.Tensor, class_idx: int) -> np.ndarray:
        self.model.zero_grad(set_to_none=True)
        with torch.enable_grad():
            x = x.clone().requires_grad_(True)
            logits = self.model(x)
            logits[0, class_idx].backward()
        weights = self.gradients.mean(dim=(2, 3), keepdim=True)
        cam = torch.relu((weights * self.activations).sum(1))[0].cpu().numpy()
        if cam.max() > 0:
            cam = cam / cam.max()
        return cam.astype(np.float32)


def overlay(rgb: np.ndarray, cam: np.ndarray, alpha: float = 0.42) -> tuple[np.ndarray, np.ndarray]:
    """Return (overlay_rgb, heatmap_rgb) at the size of rgb."""
    h, w = rgb.shape[:2]
    cam_r = cv2.resize(cam, (w, h), interpolation=cv2.INTER_CUBIC)
    heat = cv2.applyColorMap(np.uint8(255 * np.clip(cam_r, 0, 1)), cv2.COLORMAP_JET)
    heat = cv2.cvtColor(heat, cv2.COLOR_BGR2RGB)
    over = cv2.addWeighted(rgb, 1 - alpha, heat, alpha, 0)
    return over, heat
