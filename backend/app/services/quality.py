"""Automatic retinal image quality assessment (IQA).

Deterministic computer-vision checks run on every uploaded photograph BEFORE any AI inference.
These are engineering heuristics with documented default thresholds. They must be calibrated against
clinician-graded gradability labels for each supported fundus camera before clinical deployment
(see docs/regulatory/05_model_evaluation.md). They are not a learned model and make no diagnostic claim.

Verdicts:
  acceptable          — all checks passed; AI analysis may proceed
  recapture_required  — at least one hard failure; the reason is explained to the technician
  inconclusive        — no hard failure but several borderline results; human judgement needed
"""
from dataclasses import asdict, dataclass

import cv2
import numpy as np

STD_WIDTH = 768  # analysis is done on a resized copy so thresholds are resolution-independent


@dataclass
class Check:
    key: str
    label: str
    value: float
    status: str  # pass | warn | fail
    message: str


def decode_image(data: bytes) -> np.ndarray:
    """Decode JPEG/PNG/TIFF bytes into an 8-bit BGR array. Handles 16-bit and greyscale TIFFs."""
    arr = np.frombuffer(data, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_UNCHANGED)
    if img is None:
        raise ValueError("File could not be decoded as an image")
    if img.dtype == np.uint16:
        img = (img / 257).astype(np.uint8)
    elif img.dtype != np.uint8:
        img = cv2.normalize(img, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    if img.ndim == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    elif img.shape[2] == 4:
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
    return img


def retina_mask(bgr: np.ndarray) -> np.ndarray:
    """Segment the circular retinal field from the dark surround (largest bright connected component)."""
    red = bgr[:, :, 2].astype(np.float32)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)
    signal = np.maximum(red, gray)
    thr = max(12.0, float(np.percentile(signal, 5)) + 8.0)
    m = (signal > thr).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    n, labels, stats, _ = cv2.connectedComponentsWithStats(m, 8)
    if n <= 1:
        return np.zeros_like(m)
    largest = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    mask = (labels == largest).astype(np.uint8)
    # fill holes (dark lesions/vessels inside the field)
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    filled = np.zeros_like(mask)
    cv2.drawContours(filled, cnts, -1, 1, thickness=cv2.FILLED)
    return filled


def assess_quality(data: bytes, min_side: int = 512) -> dict:
    bgr0 = decode_image(data)
    h0, w0 = bgr0.shape[:2]
    checks: list[Check] = []

    # 1. Resolution
    short = min(h0, w0)
    if short < min_side:
        checks.append(Check("resolution", "Resolution", short, "fail",
                            f"Image is {w0}×{h0}px; at least {min_side}px on the short side is required."))
    elif short < 1000:
        checks.append(Check("resolution", "Resolution", short, "warn",
                            f"{w0}×{h0}px is usable but below the recommended 1000px short side."))
    else:
        checks.append(Check("resolution", "Resolution", short, "pass", f"{w0}×{h0}px."))

    scale = STD_WIDTH / w0
    bgr = cv2.resize(bgr0, (STD_WIDTH, max(1, int(round(h0 * scale)))), interpolation=cv2.INTER_AREA)
    h, w = bgr.shape[:2]
    mask = retina_mask(bgr)
    mask_bool = mask.astype(bool)
    frac = float(mask_bool.mean())

    # 2. Retinal visibility / field of view
    if frac < 0.20:
        checks.append(Check("retinal_visibility", "Retinal visibility", round(frac, 3), "fail",
                            "The retinal field occupies too little of the frame or is not visible. "
                            "Confirm a fundus camera was used and the pupil was aligned."))
    elif frac < 0.35:
        checks.append(Check("retinal_visibility", "Retinal visibility", round(frac, 3), "warn",
                            "Retinal field is smaller than expected (possible small pupil or misalignment)."))
    else:
        checks.append(Check("retinal_visibility", "Retinal visibility", round(frac, 3), "pass",
                            f"Retinal field covers {frac:.0%} of the frame."))

    if frac < 0.05:  # nothing to analyse further
        return _verdict(checks, w0, h0, extra={"retina_fraction": frac})

    ys, xs = np.nonzero(mask)
    cy, cx = ys.mean() / h, xs.mean() / w
    offset = float(np.hypot(cy - 0.5, cx - 0.5))
    pix = bgr[mask_bool]
    b_mean, g_mean, r_mean = (float(pix[:, i].mean()) for i in range(3))

    # 3. Field of view centring
    if offset > 0.20:
        checks.append(Check("field_of_view", "Field of view", round(offset, 3), "fail",
                            "Retinal field is badly off-centre; re-align the camera and recapture."))
    elif offset > 0.10:
        checks.append(Check("field_of_view", "Field of view", round(offset, 3), "warn", "Retinal field is somewhat off-centre."))
    else:
        checks.append(Check("field_of_view", "Field of view", round(offset, 3), "pass", "Retinal field is centred."))

    # 4. Colour-fundus plausibility (fundus images are red-dominant). Guards against non-fundus uploads.
    plausible = r_mean > g_mean * 1.15 and r_mean > b_mean * 1.3
    checks.append(Check("fundus_plausibility", "Fundus image plausibility", round(r_mean / max(g_mean, 1), 2),
                        "pass" if plausible else "fail",
                        "Colour profile is consistent with a colour fundus photograph." if plausible else
                        "Colour profile is not consistent with a colour fundus photograph. Only images from a "
                        "retinal fundus camera are supported."))

    green = bgr[:, :, 1]
    lum = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    inner = cv2.erode(mask, np.ones((15, 15), np.uint8)).astype(bool)
    if inner.sum() < 1000:
        inner = mask_bool

    # 5. Brightness
    bright = float(lum[inner].mean())
    if bright < 35:
        checks.append(Check("brightness", "Brightness", round(bright, 1), "fail", "Image is too dark (under-illuminated)."))
    elif bright > 200:
        checks.append(Check("brightness", "Brightness", round(bright, 1), "fail", "Image is too bright (washed out)."))
    elif bright < 55 or bright > 170:
        checks.append(Check("brightness", "Brightness", round(bright, 1), "warn", "Brightness is outside the optimal range."))
    else:
        checks.append(Check("brightness", "Brightness", round(bright, 1), "pass", "Brightness is within range."))

    # 6. Contrast (green channel carries most retinal detail)
    contrast = float(green[inner].std())
    if contrast < 8:
        checks.append(Check("contrast", "Contrast", round(contrast, 1), "fail", "Contrast is too low to visualise retinal structures."))
    elif contrast < 14:
        checks.append(Check("contrast", "Contrast", round(contrast, 1), "warn", "Contrast is low."))
    else:
        checks.append(Check("contrast", "Contrast", round(contrast, 1), "pass", "Contrast is adequate."))

    # 7. Exposure (clipping)
    clipped = float((lum[inner] >= 250).mean())
    crushed = float((lum[inner] <= 8).mean())
    exp_val = round(max(clipped, crushed), 4)
    if clipped > 0.08 or crushed > 0.15:
        checks.append(Check("exposure", "Exposure", exp_val, "fail",
                            f"Exposure clipping detected ({clipped:.0%} over-exposed, {crushed:.0%} under-exposed)."))
    elif clipped > 0.02 or crushed > 0.05:
        checks.append(Check("exposure", "Exposure", exp_val, "warn", "Some exposure clipping."))
    else:
        checks.append(Check("exposure", "Exposure", exp_val, "pass", "No significant clipping."))

    # 8. Blur / focus — variance of Laplacian and high-frequency energy on the green channel inside the field
    g_eq = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(green)
    lap = cv2.Laplacian(g_eq, cv2.CV_64F)
    lap_var = float(lap[inner].var())
    gx = cv2.Sobel(g_eq, cv2.CV_64F, 1, 0)
    gy = cv2.Sobel(g_eq, cv2.CV_64F, 0, 1)
    tenengrad = float(np.mean((gx ** 2 + gy ** 2)[inner]))
    if lap_var < 15:
        checks.append(Check("blur", "Blur / sharpness", round(lap_var, 1), "fail", "Image is blurred; vessels are not sharply defined."))
    elif lap_var < 40:
        checks.append(Check("blur", "Blur / sharpness", round(lap_var, 1), "warn", "Image is slightly soft."))
    else:
        checks.append(Check("blur", "Blur / sharpness", round(lap_var, 1), "pass", "Image is sharp."))
    if tenengrad < 150:
        checks.append(Check("focus", "Focus", round(tenengrad, 1), "fail", "Focus is poor (low edge energy). Refocus and recapture."))
    elif tenengrad < 400:
        checks.append(Check("focus", "Focus", round(tenengrad, 1), "warn", "Focus is marginal."))
    else:
        checks.append(Check("focus", "Focus", round(tenengrad, 1), "pass", "Focus is adequate."))

    # 9. Artefacts — uneven illumination across quadrants and large specular / reflex blobs
    quad_means = []
    for qy in (0, 1):
        for qx in (0, 1):
            sl = (slice(qy * h // 2, (qy + 1) * h // 2), slice(qx * w // 2, (qx + 1) * w // 2))
            q = inner[sl]
            if q.sum() > 200:
                quad_means.append(float(lum[sl][q].mean()))
    unevenness = (max(quad_means) - min(quad_means)) / max(np.mean(quad_means), 1) if len(quad_means) >= 2 else 0.0
    spec = ((lum >= 245) & inner).astype(np.uint8)
    n, _, stats, _ = cv2.connectedComponentsWithStats(spec, 8)
    big_spec = int(sum(1 for i in range(1, n) if stats[i, cv2.CC_STAT_AREA] > 0.004 * inner.sum()))
    artefact_score = round(float(unevenness), 3)
    if unevenness > 0.9 or big_spec >= 3:
        checks.append(Check("artefacts", "Artefacts", artefact_score, "fail",
                            "Strong artefacts detected (uneven illumination, eyelash shadow or reflections)."))
    elif unevenness > 0.55 or big_spec >= 1:
        checks.append(Check("artefacts", "Artefacts", artefact_score, "warn",
                            "Possible artefacts (uneven illumination or reflections)."))
    else:
        checks.append(Check("artefacts", "Artefacts", artefact_score, "pass", "No significant artefacts detected."))

    return _verdict(checks, w0, h0, extra={"retina_fraction": round(frac, 3), "mean_rgb": [round(r_mean, 1), round(g_mean, 1), round(b_mean, 1)]})


def _verdict(checks: list[Check], w: int, h: int, extra: dict) -> dict:
    fails = [c for c in checks if c.status == "fail"]
    warns = [c for c in checks if c.status == "warn"]
    if fails:
        verdict, summary = "recapture_required", "Recapture required: " + " ".join(c.message for c in fails)
    elif len(warns) >= 3:
        verdict, summary = "inconclusive", "Quality is borderline on several checks; a clinician should decide whether the image is gradable."
    else:
        verdict, summary = "acceptable", "Image quality is acceptable for AI-assisted screening."
    return {"verdict": verdict, "summary": summary, "width": w, "height": h, "checks": [asdict(c) for c in checks],
            "method": "netrarakshak-iqa-heuristic v1.0 (uncalibrated defaults)", **extra}
