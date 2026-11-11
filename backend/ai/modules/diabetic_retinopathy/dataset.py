"""Dataset preparation for DR grading.

Supported label formats (verify the licence of each dataset for your intended use — see docs/datasets.md):
  * APTOS 2019 Blindness Detection (Kaggle): train.csv with columns id_code, diagnosis; images <id_code>.png
  * EyePACS / Kaggle DR Detection 2015: trainLabels.csv with columns image, level; images <image>.jpeg
  * Generic: CSV with columns image_path, label (0-4 ICDR), optional patient_id
All formats are normalised to: path, label, patient_id. Splits are made at PATIENT level (both eyes of a
patient stay in the same split) and stratified by grade to prevent leakage.
"""
import hashlib
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
import torch
from sklearn.model_selection import StratifiedGroupKFold
from torch.utils.data import Dataset, WeightedRandomSampler

from ai.common.preprocess import preprocess_bgr, to_tensor

IMG_EXTS = (".png", ".jpg", ".jpeg", ".tif", ".tiff")


def _find(images_dir: Path, stem: str) -> Path | None:
    for ext in IMG_EXTS:
        p = images_dir / f"{stem}{ext}"
        if p.exists():
            return p
    return None


def load_labels(csv_path: str, images_dir: str, fmt: str = "auto") -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    images = Path(images_dir)
    if fmt == "auto":
        fmt = "aptos" if "id_code" in df else "eyepacs" if "level" in df else "generic"
    if fmt == "aptos":
        out = pd.DataFrame({"stem": df["id_code"].astype(str), "label": df["diagnosis"].astype(int)})
        out["patient_id"] = out["stem"]  # APTOS does not publish patient IDs; image-level grouping
    elif fmt == "eyepacs":
        out = pd.DataFrame({"stem": df["image"].astype(str), "label": df["level"].astype(int)})
        out["patient_id"] = out["stem"].str.rsplit("_", n=1).str[0]  # "10_left" -> "10"
    else:
        out = pd.DataFrame({"path": df["image_path"].astype(str), "label": df["label"].astype(int)})
        out["patient_id"] = df["patient_id"].astype(str) if "patient_id" in df else out["path"]
        out["path"] = [str(p if Path(p).is_absolute() else images / p) for p in out["path"]]
    if "path" not in out:
        out["path"] = [str(_find(images, s) or "") for s in out["stem"]]
    missing = (out["path"] == "").sum()
    out = out[out["path"] != ""].reset_index(drop=True)
    if not ((out["label"] >= 0) & (out["label"] <= 4)).all():
        raise ValueError("Labels must be ICDR grades 0-4")
    out.attrs["missing_images"] = int(missing)
    out.attrs["format"] = fmt
    return out[["path", "label", "patient_id"]]


def patient_split(df: pd.DataFrame, val_frac=0.15, test_frac=0.15, seed=42) -> dict[str, pd.DataFrame]:
    """Stratified, patient-grouped train/val/test split."""
    def take(frame, frac, seed_):
        n_splits = max(2, int(round(1 / frac)))
        sgkf = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=seed_)
        rest_idx, hold_idx = next(sgkf.split(frame, frame["label"], frame["patient_id"]))
        return frame.iloc[rest_idx].reset_index(drop=True), frame.iloc[hold_idx].reset_index(drop=True)
    rest, test = take(df, test_frac, seed)
    train, val = take(rest, val_frac / (1 - test_frac), seed + 1)
    assert not set(train.patient_id) & set(test.patient_id), "patient leakage train/test"
    assert not set(train.patient_id) & set(val.patient_id), "patient leakage train/val"
    return {"train": train, "val": val, "test": test}


class FundusAugment:
    """Fundus-appropriate augmentation: geometric (rotation/flip/scale) + mild photometric. No colour inversion.
    A class (not a closure) so it can be pickled by DataLoader workers on Windows (spawn start method)."""

    def __init__(self, size: int):
        self.size = size

    def __call__(self, rgb: np.ndarray) -> np.ndarray:
        rng = np.random.default_rng()
        size = self.size
        if rng.random() < 0.5:
            rgb = rgb[:, ::-1]
        if rng.random() < 0.5:
            rgb = rgb[::-1]
        M = cv2.getRotationMatrix2D((size / 2, size / 2), rng.uniform(-180, 180), rng.uniform(0.92, 1.10))
        rgb = cv2.warpAffine(np.ascontiguousarray(rgb), M, (size, size), borderValue=(128, 128, 128))
        alpha, beta = rng.uniform(0.85, 1.15), rng.uniform(-15, 15)
        return np.clip(rgb.astype(np.float32) * alpha + beta, 0, 255).astype(np.uint8)


def build_augment(size: int) -> FundusAugment:
    return FundusAugment(size)


class FundusDataset(Dataset):
    def __init__(self, df: pd.DataFrame, size: int, train: bool, use_ben_graham: bool = True, cache_dir: str | None = None):
        self.df = df.reset_index(drop=True)
        self.size = size
        self.train = train
        self.bg = use_ben_graham
        self.aug = build_augment(size) if train else None
        self.cache = Path(cache_dir) if cache_dir else None
        if self.cache:
            self.cache.mkdir(parents=True, exist_ok=True)

    def __len__(self):
        return len(self.df)

    def _load(self, path: str) -> np.ndarray:
        if self.cache:
            cp = self.cache / f"{hashlib.md5(path.encode()).hexdigest()}_{self.size}_{int(self.bg)}.png"
            if cp.exists():
                return cv2.cvtColor(cv2.imread(str(cp)), cv2.COLOR_BGR2RGB)
        bgr = cv2.imread(path, cv2.IMREAD_COLOR)
        if bgr is None:
            raise FileNotFoundError(path)
        rgb = preprocess_bgr(bgr, self.size, self.bg)
        if self.cache:
            cv2.imwrite(str(cp), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
        return rgb

    def __getitem__(self, i):
        row = self.df.iloc[i]
        rgb = self._load(row.path)
        if self.aug:
            rgb = self.aug(rgb)
        return to_tensor(rgb), int(row.label)


def class_weights(labels: np.ndarray, k: int = 5) -> torch.Tensor:
    counts = np.bincount(labels, minlength=k).astype(np.float32)
    counts[counts == 0] = 1
    w = counts.sum() / (k * counts)
    return torch.tensor(w / w.mean(), dtype=torch.float32)


def balanced_sampler(labels: np.ndarray, k: int = 5) -> WeightedRandomSampler:
    w = class_weights(labels, k).numpy()[labels]
    return WeightedRandomSampler(torch.as_tensor(w, dtype=torch.double), num_samples=len(labels), replacement=True)
