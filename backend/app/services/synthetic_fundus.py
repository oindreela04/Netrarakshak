"""Procedurally generated *synthetic* fundus-like images for automated tests and UI demos ONLY.

These images are NOT real retinal photographs, carry no clinical meaning and must never be used to
evaluate or claim model performance. Every file produced is stamped "SYNTHETIC" in its metadata and
filename. They exist so that the upload → quality → pipeline → report workflow can be tested without
patient data.
"""
import cv2
import numpy as np


def make_synthetic_fundus(size: int = 1024, seed: int = 0, lesions: int = 0, blur: float = 0.0,
                          brightness: float = 1.0, eye: str = "right") -> np.ndarray:
    rng = np.random.default_rng(seed)
    img = np.zeros((size, size, 3), np.float32)
    c = size // 2
    r = int(size * 0.46)
    yy, xx = np.mgrid[0:size, 0:size]
    d = np.sqrt((yy - c) ** 2 + (xx - c) ** 2) / r
    inside = d <= 1.0
    vign = np.clip(1.0 - 0.45 * d ** 2, 0, 1)
    base = np.array([30, 75, 185], np.float32)  # BGR orange-red
    base = base * (0.9 + 0.2 * rng.random(3))
    for ch in range(3):
        img[:, :, ch] = base[ch] * vign
    tex = cv2.GaussianBlur(rng.normal(0, 1, (size, size)).astype(np.float32), (0, 0), size / 120)
    img += (tex * 18)[:, :, None] * np.array([0.3, 0.6, 1.0])

    # optic disc (nasal side differs by eye) and macula
    disc_x = c + int(r * (0.42 if eye == "right" else -0.42)) + int(rng.integers(-10, 10))
    disc_y = c + int(rng.integers(-15, 15))
    dd = np.sqrt((yy - disc_y) ** 2 + (xx - disc_x) ** 2)
    disc = np.clip(1 - dd / (size * 0.075), 0, 1) ** 0.7
    img += disc[:, :, None] * np.array([90, 120, 70])
    mac_x = c - int(r * (0.08 if eye == "right" else -0.08))
    md = np.sqrt((yy - c) ** 2 + (xx - mac_x) ** 2)
    img *= (1 - 0.35 * np.clip(1 - md / (size * 0.09), 0, 1))[:, :, None]

    # vessel tree: random walks from the disc
    vessels = np.zeros((size, size), np.float32)
    for k in range(12):
        ang = (k / 12) * 2 * np.pi + rng.normal(0, 0.2)
        x, y = float(disc_x), float(disc_y)
        width = int(rng.integers(3, 8))
        for _ in range(140):
            ang += rng.normal(0, 0.12)
            nx, ny = x + np.cos(ang) * size / 160, y + np.sin(ang) * size / 160
            cv2.line(vessels, (int(x), int(y)), (int(nx), int(ny)), 1.0, max(1, width))
            x, y = nx, ny
            if rng.random() < 0.03:
                width = max(1, width - 1)
    vessels = cv2.GaussianBlur(vessels, (0, 0), 1.2)
    img *= (1 - 0.5 * vessels)[:, :, None]

    # synthetic "lesion-like" dots (no clinical meaning)
    for _ in range(lesions):
        lx, ly = int(c + rng.normal(0, r * 0.4)), int(c + rng.normal(0, r * 0.4))
        if inside[min(max(ly, 0), size - 1), min(max(lx, 0), size - 1)]:
            if rng.random() < 0.5:
                cv2.circle(img, (lx, ly), int(rng.integers(3, 9)), (20, 20, 110), -1)
            else:
                cv2.circle(img, (lx, ly), int(rng.integers(3, 7)), (120, 210, 230), -1)

    img *= brightness
    img[~inside] = 0
    img = np.clip(img + rng.normal(0, 2.0, img.shape), 0, 255).astype(np.uint8)
    img[~inside] = 0
    if blur > 0:
        img = cv2.GaussianBlur(img, (0, 0), blur)
    return img


def encode(img: np.ndarray, ext: str = ".png") -> bytes:
    ok, buf = cv2.imencode(ext, img)
    assert ok
    return buf.tobytes()
