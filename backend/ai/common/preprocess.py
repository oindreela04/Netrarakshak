"""Fundus preprocessing shared by training and inference (identical code path = no train/serve skew)."""
import cv2
import numpy as np
import torch

IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], np.float32)
IMAGENET_STD = np.array([0.229, 0.224, 0.225], np.float32)


def crop_to_retina(bgr: np.ndarray, tol: int = 10) -> np.ndarray:
    """Remove the black border around the circular retinal field."""
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    mask = gray > tol
    if not mask.any():
        return bgr
    rows, cols = np.where(mask.any(1))[0], np.where(mask.any(0))[0]
    return bgr[rows[0]:rows[-1] + 1, cols[0]:cols[-1] + 1]


def pad_square(img: np.ndarray) -> np.ndarray:
    h, w = img.shape[:2]
    s = max(h, w)
    out = np.zeros((s, s, 3), img.dtype)
    out[(s - h) // 2:(s - h) // 2 + h, (s - w) // 2:(s - w) // 2 + w] = img
    return out


def ben_graham(bgr: np.ndarray, sigma_frac: float = 1 / 30) -> np.ndarray:
    """Local-average colour subtraction (Graham, Kaggle DR 2015). Normalises illumination across cameras."""
    s = bgr.shape[0]
    blur = cv2.GaussianBlur(bgr, (0, 0), s * sigma_frac)
    out = cv2.addWeighted(bgr, 4, blur, -4, 128)
    yy, xx = np.mgrid[0:s, 0:s]
    circle = ((yy - s / 2) ** 2 + (xx - s / 2) ** 2) <= (0.48 * s) ** 2
    out[~circle] = 128
    return out


def preprocess_bgr(bgr: np.ndarray, size: int, use_ben_graham: bool = True) -> np.ndarray:
    """BGR uint8 (any size) → RGB uint8 (size×size) ready for augmentation / tensor conversion."""
    img = pad_square(crop_to_retina(bgr))
    img = cv2.resize(img, (size, size), interpolation=cv2.INTER_AREA)
    if use_ben_graham:
        img = ben_graham(img)
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)


def to_tensor(rgb: np.ndarray) -> torch.Tensor:
    x = (rgb.astype(np.float32) / 255.0 - IMAGENET_MEAN) / IMAGENET_STD
    return torch.from_numpy(x.transpose(2, 0, 1).copy())
