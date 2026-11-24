"""NetraRakshak – multi-disease fundus model (ODIR-5K) – paste this whole file into ONE Kaggle notebook cell.

Steps on kaggle.com (free GPU, about 30–45 minutes):
  1. New Notebook.  Right panel → Session options: Accelerator = GPU T4 x2 (or P100), Internet = On.
  2. "+ Add Input" → search "ocular disease recognition odir5k" (by andrewmvd) → Add.
  3. Paste this file into the first cell and press Run (Shift+Enter).
  4. When it prints "DONE", open the Output panel (right side, /kaggle/working) and download
     netrarakshak_multidisease_model.zip.  Send that zip to Claude (or unzip it into backend/ai/model_registry/).

What it does: reads the ODIR-5K per-eye diagnostic keywords, builds 8 labels per eye
(N normal, D diabetic retinopathy, G glaucoma, C cataract, A AMD, H hypertensive retinopathy, M pathological myopia,
O other abnormality), splits by PATIENT into train/val/test (70/15/15, seed 42), fine-tunes an ImageNet
EfficientNet-B0 at 384 px with the same preprocessing the NetraRakshak server uses, picks per-class decision
thresholds on the validation set, and reports held-out test metrics (AUC, sensitivity, specificity, F1).
"""
import glob, hashlib, json, math, os, random, re, shutil, time, zipfile
from datetime import datetime, timezone
from multiprocessing import Pool
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torchvision
from sklearn.metrics import f1_score, roc_auc_score

SEED, SIZE, EPOCHS, BATCH, LR = 42, int(os.getenv("NR_SIZE", 384)), int(os.getenv("NR_EPOCHS", 14)), 32, 3e-4
random.seed(SEED); np.random.seed(SEED); torch.manual_seed(SEED)
WORK = os.getenv("NR_WORK", "/kaggle/working")
DEV = "cuda" if torch.cuda.is_available() else "cpu"
print("device:", DEV, torch.cuda.get_device_name(0) if DEV == "cuda" else "")
assert DEV == "cuda" or os.getenv("NR_CPU_TEST"), "Turn on the GPU accelerator in Session options, then run again."

CLASS_KEYS = ["normal", "diabetic_retinopathy", "glaucoma", "cataract", "amd", "hypertensive_retinopathy",
              "pathological_myopia", "other"]
CLASS_NAMES = ["Normal fundus", "Diabetic retinopathy", "Glaucoma (suspect)", "Cataract / media opacity",
               "Age-related macular degeneration", "Hypertensive retinopathy", "Pathological myopia",
               "Other abnormality"]

# ---------------------------------------------------------------- 1. locate data
inp = Path(os.getenv("NR_INPUT", "/kaggle/input"))
xlsx = next(iter(glob.glob(str(inp / "**/data.xlsx"), recursive=True)), None)
csv = next(iter(glob.glob(str(inp / "**/full_df.csv"), recursive=True)), None)
assert xlsx or csv, "ODIR-5K not found – add the dataset 'ocular-disease-recognition-odir5k' as an input."
df = pd.read_excel(xlsx) if xlsx else pd.read_csv(csv)
df = df.drop_duplicates(subset=["ID"])
img_dirs = [d for d in glob.glob(str(inp / "**/*"), recursive=True)
            if os.path.isdir(d) and re.search(r"(Training Images|preprocessed_images)$", d)]
img_dirs.sort(key=lambda d: 0 if "Training Images" in d else 1)
print("label file:", xlsx or csv, "| image folders:", img_dirs)


def find(name):
    for d in img_dirs:
        p = os.path.join(d, name)
        if os.path.exists(p):
            return p
    return None


# ---------------------------------------------------------------- 2. per-eye labels from keywords
IGNORE = ("lens dust", "low image quality", "image offset", "optic disk photographically invisible",
          "no fundus image", "anterior segment image")


def eye_labels(kw: str):
    kws = [k.strip().lower() for k in re.split(r"[，,;]", str(kw)) if k.strip()]
    if any(k in ("no fundus image", "anterior segment image") for k in kws):
        return None  # not a usable fundus photograph
    y = np.zeros(8, np.float32)
    for k in kws:
        if k in IGNORE:
            continue
        if "normal fundus" in k:
            y[0] = 1
        elif "hypertensive" in k:
            y[5] = 1
        elif "retinopathy" in k and "diabetic" in k or "proliferative" in k or "nonproliferative" in k:
            y[1] = 1
        elif "glaucoma" in k:
            y[2] = 1
        elif "cataract" in k:
            y[3] = 1
        elif "macular degeneration" in k:
            y[4] = 1
        elif "myopi" in k:
            y[6] = 1
        else:
            y[7] = 1
    if y[1:].any():
        y[0] = 0  # "normal" never co-occurs with a finding
    return y if y.any() else None


rows = []
for _, r in df.iterrows():
    for side, fcol, kcol in (("left", "Left-Fundus", "Left-Diagnostic Keywords"),
                             ("right", "Right-Fundus", "Right-Diagnostic Keywords")):
        y = eye_labels(r[kcol])
        p = find(str(r[fcol]))
        if y is not None and p:
            rows.append({"pid": int(r["ID"]), "path": p, "eye": side, "y": y})
print(f"usable eye images: {len(rows)}  from {df.shape[0]} patients")
Y = np.stack([r["y"] for r in rows])
print("label counts:", dict(zip(CLASS_KEYS, Y.sum(0).astype(int).tolist())))

# ---------------------------------------------------------------- 3. patient-level split 70/15/15
pids = sorted({r["pid"] for r in rows})
rng = np.random.RandomState(SEED); rng.shuffle(pids)
n = len(pids); tr_p = set(pids[:int(.70 * n)]); va_p = set(pids[int(.70 * n):int(.85 * n)])
split = np.array(["train" if r["pid"] in tr_p else "val" if r["pid"] in va_p else "test" for r in rows])
for s in ("train", "val", "test"):
    print(s, (split == s).sum(), "images", dict(zip(CLASS_KEYS, Y[split == s].sum(0).astype(int).tolist())))


# ---------------------------------------------------------------- 4. preprocessing (identical to the server)
def crop_to_retina(bgr, tol=10):
    g = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY); m = g > tol
    if not m.any():
        return bgr
    rr, cc = np.where(m.any(1))[0], np.where(m.any(0))[0]
    return bgr[rr[0]:rr[-1] + 1, cc[0]:cc[-1] + 1]


def pad_square(img):
    h, w = img.shape[:2]; s = max(h, w); out = np.zeros((s, s, 3), img.dtype)
    out[(s - h) // 2:(s - h) // 2 + h, (s - w) // 2:(s - w) // 2 + w] = img
    return out


def ben_graham(bgr, sigma_frac=1 / 30):
    s = bgr.shape[0]; blur = cv2.GaussianBlur(bgr, (0, 0), s * sigma_frac)
    out = cv2.addWeighted(bgr, 4, blur, -4, 128)
    yy, xx = np.mgrid[0:s, 0:s]; out[((yy - s / 2) ** 2 + (xx - s / 2) ** 2) > (0.48 * s) ** 2] = 128
    return out


def prep(path):
    bgr = cv2.imread(path, cv2.IMREAD_COLOR)
    img = cv2.resize(pad_square(crop_to_retina(bgr)), (SIZE, SIZE), interpolation=cv2.INTER_AREA)
    return cv2.cvtColor(ben_graham(img), cv2.COLOR_BGR2RGB)


t0 = time.time()
with Pool(os.cpu_count()) as pool:
    X = np.stack(pool.map(prep, [r["path"] for r in rows], chunksize=32))
print(f"preprocessed {len(X)} images in {time.time() - t0:.0f}s  ({X.nbytes / 1e9:.1f} GB in RAM)")

MEAN = torch.tensor([0.485, 0.456, 0.406]).view(1, 3, 1, 1).to(DEV)
STD = torch.tensor([0.229, 0.224, 0.225]).view(1, 3, 1, 1).to(DEV)


def batch_tensor(idx, augment):
    xb = torch.from_numpy(X[idx]).to(DEV).permute(0, 3, 1, 2).float() / 255.0
    if augment:
        if random.random() < .5: xb = xb.flip(3)
        if random.random() < .5: xb = xb.flip(2)
        k = random.randint(0, 3); xb = torch.rot90(xb, k, (2, 3))
        xb = (xb * torch.empty(len(idx), 1, 1, 1, device=DEV).uniform_(.85, 1.15)
              + torch.empty(len(idx), 1, 1, 1, device=DEV).uniform_(-.06, .06)).clamp(0, 1)
    return (xb - MEAN) / STD


# ---------------------------------------------------------------- 5. model and training
model = torchvision.models.efficientnet_b0(weights=None if os.getenv("NR_NO_PRETRAINED") else torchvision.models.EfficientNet_B0_Weights.IMAGENET1K_V1)
model.classifier = nn.Sequential(nn.Dropout(0.3), nn.Linear(model.classifier[1].in_features, 8))
model = model.to(DEV)
tr_idx, va_idx, te_idx = [np.where(split == s)[0] for s in ("train", "val", "test")]
pos = Y[tr_idx].sum(0); neg = len(tr_idx) - pos
crit = nn.BCEWithLogitsLoss(pos_weight=torch.tensor(np.clip(neg / np.maximum(pos, 1), 1, 15), device=DEV))
opt = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=1e-4)
steps = EPOCHS * math.ceil(len(tr_idx) / BATCH)
sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=LR, total_steps=steps, pct_start=0.15)
scaler = torch.amp.GradScaler(enabled=DEV == "cuda")


@torch.no_grad()
def predict(idx):
    model.eval(); out = []
    for i in range(0, len(idx), 64):
        with torch.autocast(device_type=DEV, dtype=torch.float16, enabled=DEV == "cuda"):
            out.append(torch.sigmoid(model(batch_tensor(idx[i:i + 64], False)).float()).cpu().numpy())
    return np.concatenate(out)


def macro_auc(y, p):
    return float(np.mean([roc_auc_score(y[:, c], p[:, c]) for c in range(8) if 0 < y[:, c].sum() < len(y)]))


best, best_state, history = -1, None, []
for ep in range(1, EPOCHS + 1):
    model.train(); perm = np.random.permutation(tr_idx); tl = 0; t0 = time.time()
    for i in range(0, len(perm), BATCH):
        b = perm[i:i + BATCH]
        with torch.autocast(device_type=DEV, dtype=torch.float16, enabled=DEV == "cuda"):
            loss = crit(model(batch_tensor(b, True)), torch.from_numpy(Y[b]).to(DEV))
        opt.zero_grad(set_to_none=True); scaler.scale(loss).backward(); scaler.step(opt); scaler.update(); sched.step()
        tl += loss.item() * len(b)
    auc = macro_auc(Y[va_idx], predict(va_idx))
    history.append({"epoch": ep, "train_loss": tl / len(tr_idx), "val_macro_auc": auc})
    print(f"epoch {ep:2d}/{EPOCHS}  loss {tl / len(tr_idx):.4f}  val macro-AUC {auc:.4f}  ({time.time() - t0:.0f}s)")
    if auc > best:
        best, best_ep = auc, ep
        best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
model.load_state_dict(best_state)
print(f"best epoch {best_ep}  val macro-AUC {best:.4f}")

# ---------------------------------------------------------------- 6. thresholds on validation, metrics on test
pv, pt = predict(va_idx), predict(te_idx)
thr = []
for c in range(8):
    cands = np.linspace(0.05, 0.95, 91)
    f1s = [f1_score(Y[va_idx, c], pv[:, c] >= t, zero_division=0) for t in cands]
    thr.append(float(cands[int(np.argmax(f1s))]))
per_class = {}
for c, k in enumerate(CLASS_KEYS):
    y, p = Y[te_idx, c], pt[:, c]; yhat = p >= thr[c]
    tp = int(((yhat == 1) & (y == 1)).sum()); tn = int(((yhat == 0) & (y == 0)).sum())
    fp = int(((yhat == 1) & (y == 0)).sum()); fn = int(((yhat == 0) & (y == 1)).sum())
    per_class[k] = {"name": CLASS_NAMES[c], "n_positive": int(y.sum()), "threshold": round(thr[c], 3),
                    "auc": round(float(roc_auc_score(y, p)), 4) if 0 < y.sum() < len(y) else None,
                    "sensitivity": round(tp / max(tp + fn, 1), 4), "specificity": round(tn / max(tn + fp, 1), 4),
                    "precision": round(tp / max(tp + fp, 1), 4),
                    "f1": round(float(f1_score(y, yhat, zero_division=0)), 4)}
test_metrics = {"n_images": int(len(te_idx)), "macro_auc": round(macro_auc(Y[te_idx], pt), 4),
                "macro_f1": round(float(np.mean([v["f1"] for v in per_class.values()])), 4), "per_class": per_class}
print(json.dumps(test_metrics, indent=1))

# ---------------------------------------------------------------- 7. write model registry entry
version = datetime.now().strftime("%Y.%m.%d-%H%M")
out = Path(WORK + "/model_registry/multi_disease") / version
out.mkdir(parents=True, exist_ok=True)
model.cpu().eval()
torch.save(model.state_dict(), out / "weights.pt")
sha = hashlib.sha256((out / "weights.pt").read_bytes()).hexdigest()
card = {
    "module": "multi_disease", "model_name": "NR-MD-efficientnet_b0", "version": version,
    "created_at": datetime.now(timezone.utc).isoformat(), "architecture": "efficientnet_b0", "input_size": SIZE,
    "output": "multi-label sigmoid", "preprocessing": "crop-to-retina, pad-square, resize, Ben Graham, ImageNet normalisation",
    "class_keys": CLASS_KEYS, "class_names": CLASS_NAMES, "thresholds": dict(zip(CLASS_KEYS, [round(t, 3) for t in thr])),
    "training_data": {"name": "ODIR-5K (Ocular Disease Intelligent Recognition, Peking University) via Kaggle",
                      "licence": "Research / academic use; commercial use NOT confirmed", "synthetic": False,
                      "label_source": "per-eye diagnostic keywords mapped to 8 categories",
                      "n_images": len(rows), "split_sizes": {"train": len(tr_idx), "val": len(va_idx), "test": len(te_idx)},
                      "split_method": "random by patient ID (both eyes of a patient in the same split), seed 42"},
    "training": {"epochs": EPOCHS, "best_epoch": best_ep, "batch_size": BATCH, "lr": LR, "optimizer": "AdamW, one-cycle",
                 "loss": "BCE with positive-class weights", "history": history},
    "evaluation": {"val_macro_auc": round(best, 4), "test_metrics": test_metrics},
    "weights_sha256": sha,
    "clinical_use_status": "NOT CLINICALLY VALIDATED — research/investigational use under clinician supervision only",
}
(out / "model_card.json").write_text(json.dumps(card, indent=2))
(out.parent / "ACTIVE").write_text(version)
zpath = WORK + "/netrarakshak_multidisease_model.zip"
with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
    for p in Path(WORK + "/model_registry").rglob("*"):
        z.write(p, p.relative_to(WORK + "/model_registry"))
print(f"DONE – download {zpath} from the Output panel ({os.path.getsize(zpath) / 1e6:.1f} MB) and send it to Claude.")
