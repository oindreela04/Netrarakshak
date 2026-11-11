"""Train, calibrate, evaluate and register a diabetic retinopathy grading model.

Example (Windows, from backend\\ with the venv active):
    python -m ai.modules.diabetic_retinopathy.train ^
        --labels D:\\datasets\\aptos2019\\train.csv --images D:\\datasets\\aptos2019\\train_images ^
        --dataset-name "APTOS 2019" --dataset-licence "Kaggle competition rules - verify" ^
        --arch efficientnet_b0 --size 384 --epochs 25 --batch-size 16

Every metric written to the model card is computed here from held-out test predictions. Nothing is typed in.
"""
import argparse
import hashlib
import json
import platform
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from ai.common.calibration import fit_temperature
from ai.common.metrics import expected_calibration_error, multiclass_metrics
from ai.modules.diabetic_retinopathy.dataset import (FundusDataset, balanced_sampler, class_weights, load_labels,
                                                    patient_split)
from ai.modules.diabetic_retinopathy.model import CLASS_KEYS, CLASS_NAMES, REFERABLE_FROM, build_model

MODULE = "diabetic_retinopathy"


def collect_logits(model, loader, device):
    model.eval()
    outs, ys = [], []
    with torch.no_grad():
        for x, y in loader:
            outs.append(model(x.to(device)).float().cpu())
            ys.append(y)
    return torch.cat(outs), torch.cat(ys)


def save_plots(metrics: dict, probs: np.ndarray, y: np.ndarray, out: Path):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from sklearn.metrics import roc_curve
    except ImportError:
        return
    cm = np.array(metrics["confusion_matrix"])
    fig, ax = plt.subplots(figsize=(6.5, 5.5))
    ax.imshow(cm, cmap="Blues")
    ax.set_xticks(range(5), CLASS_NAMES, rotation=35, ha="right", fontsize=8)
    ax.set_yticks(range(5), CLASS_NAMES, fontsize=8)
    for i in range(5):
        for j in range(5):
            ax.text(j, i, cm[i, j], ha="center", va="center", fontsize=9,
                    color="white" if cm[i, j] > cm.max() / 2 else "black")
    ax.set_xlabel("Predicted"); ax.set_ylabel("Reference grade"); ax.set_title("Test confusion matrix")
    fig.tight_layout(); fig.savefig(out / "confusion_matrix.png", dpi=150); plt.close(fig)

    fig, ax = plt.subplots(figsize=(5.5, 5))
    for i, n in enumerate(CLASS_NAMES):
        if (y == i).any() and (y != i).any():
            fpr, tpr, _ = roc_curve((y == i).astype(int), probs[:, i])
            ax.plot(fpr, tpr, label=n)
    yb = (y >= REFERABLE_FROM).astype(int)
    if 0 < yb.sum() < len(yb):
        fpr, tpr, _ = roc_curve(yb, probs[:, REFERABLE_FROM:].sum(1))
        ax.plot(fpr, tpr, "k--", lw=2, label="Referable DR")
    ax.plot([0, 1], [0, 1], ":", color="grey")
    ax.set_xlabel("1 - specificity"); ax.set_ylabel("Sensitivity"); ax.set_title("Test ROC"); ax.legend(fontsize=7)
    fig.tight_layout(); fig.savefig(out / "roc_curves.png", dpi=150); plt.close(fig)


def file_sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--labels", required=True)
    ap.add_argument("--images", required=True)
    ap.add_argument("--format", default="auto", choices=["auto", "aptos", "eyepacs", "generic"])
    ap.add_argument("--dataset-name", required=True)
    ap.add_argument("--dataset-licence", required=True, help="Licence/terms under which the data is used")
    ap.add_argument("--synthetic", action="store_true", help="Mark as synthetic (pipeline smoke test only)")
    ap.add_argument("--arch", default="efficientnet_b0")
    ap.add_argument("--no-pretrained", action="store_true")
    ap.add_argument("--size", type=int, default=384)
    ap.add_argument("--epochs", type=int, default=25)
    ap.add_argument("--batch-size", type=int, default=16)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--weight-decay", type=float, default=1e-4)
    ap.add_argument("--imbalance", default="weighted_loss", choices=["weighted_loss", "sampler", "none"])
    ap.add_argument("--patience", type=int, default=6)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--version", default=None)
    ap.add_argument("--work-dir", default="ai/runs")
    ap.add_argument("--registry", default="ai/model_registry")
    ap.add_argument("--no-activate", action="store_true", help="Register without making it the active model")
    ap.add_argument("--cache-dir", default=None)
    args = ap.parse_args(argv)

    torch.manual_seed(args.seed); np.random.seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    version = args.version or datetime.now().strftime("%Y.%m.%d-%H%M")
    run = Path(args.work_dir) / f"{MODULE}-{version}"
    run.mkdir(parents=True, exist_ok=True)

    df = load_labels(args.labels, args.images, args.format)
    print(f"[data] {len(df)} labelled images ({df.attrs.get('missing_images', 0)} label rows without image files)")
    splits = patient_split(df, seed=args.seed)
    for k, v in splits.items():
        v.to_csv(run / f"split_{k}.csv", index=False)
        print(f"[data] {k}: {len(v)} images, grade counts {np.bincount(v.label, minlength=5).tolist()}")

    mk = lambda d, tr: FundusDataset(d, args.size, tr, cache_dir=args.cache_dir)
    ytr = splits["train"].label.to_numpy()
    sampler = balanced_sampler(ytr) if args.imbalance == "sampler" else None
    dl_train = DataLoader(mk(splits["train"], True), batch_size=args.batch_size, shuffle=sampler is None,
                          sampler=sampler, num_workers=args.workers, pin_memory=device.type == "cuda", drop_last=len(ytr) > args.batch_size)
    dl_val = DataLoader(mk(splits["val"], False), batch_size=args.batch_size, num_workers=args.workers)
    dl_test = DataLoader(mk(splits["test"], False), batch_size=args.batch_size, num_workers=args.workers)

    model = build_model(args.arch, pretrained=not args.no_pretrained).to(device)
    cw = class_weights(ytr).to(device) if args.imbalance == "weighted_loss" else None
    crit = nn.CrossEntropyLoss(weight=cw, label_smoothing=0.05)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=args.lr, total_steps=max(1, args.epochs * len(dl_train)), pct_start=0.15)
    scaler = torch.amp.GradScaler("cuda", enabled=device.type == "cuda")

    best, best_epoch, stale, history = -1e9, -1, 0, []
    for epoch in range(1, args.epochs + 1):
        model.train()
        t0, tot, n = time.time(), 0.0, 0
        for x, y in dl_train:
            x, y = x.to(device), y.to(device)
            opt.zero_grad(set_to_none=True)
            with torch.autocast(device.type, enabled=device.type == "cuda"):
                loss = crit(model(x), y)
            scaler.scale(loss).backward()
            scaler.step(opt); scaler.update(); sched.step()
            tot += loss.item() * len(y); n += len(y)
        vl, vy = collect_logits(model, dl_val, device)
        vm = multiclass_metrics(vy.numpy(), torch.softmax(vl, 1).numpy(), CLASS_NAMES, REFERABLE_FROM)
        score = vm["quadratic_weighted_kappa"]
        history.append({"epoch": epoch, "train_loss": tot / max(n, 1), "val_qwk": score, "val_accuracy": vm["accuracy"],
                        "seconds": round(time.time() - t0, 1)})
        print(f"[epoch {epoch}] loss {tot / max(n, 1):.4f}  val QWK {score:.4f}  val acc {vm['accuracy']:.4f}")
        if score > best:
            best, best_epoch, stale = score, epoch, 0
            torch.save(model.state_dict(), run / "best.pt")
        else:
            stale += 1
            if stale >= args.patience:
                print("[train] early stopping")
                break

    model.load_state_dict(torch.load(run / "best.pt", map_location=device, weights_only=True))
    vl, vy = collect_logits(model, dl_val, device)
    T = fit_temperature(vl, vy)
    tl, ty = collect_logits(model, dl_test, device)
    probs_raw = torch.softmax(tl, 1).numpy()
    probs = torch.softmax(tl / T, 1).numpy()
    yt = ty.numpy()
    test_metrics = multiclass_metrics(yt, probs, CLASS_NAMES, REFERABLE_FROM)
    test_metrics["ece_before_calibration"] = expected_calibration_error(probs_raw, yt)
    test_metrics["ece_after_calibration"] = expected_calibration_error(probs, yt)
    save_plots(test_metrics, probs, yt, run)
    np.savez(run / "test_predictions.npz", y=yt, probs=probs)

    card = {
        "module": MODULE, "model_name": f"NR-DR-{args.arch}", "version": version,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "architecture": args.arch, "input_size": args.size, "preprocessing": "crop-to-retina, pad-square, resize, Ben Graham local-average subtraction, ImageNet normalisation",
        "class_keys": CLASS_KEYS, "class_names": CLASS_NAMES, "referable_from": REFERABLE_FROM,
        "temperature": T,
        "training_data": {"name": args.dataset_name, "licence": args.dataset_licence, "synthetic": bool(args.synthetic),
                          "label_format": df.attrs.get("format"), "n_images": int(len(df)),
                          "split_sizes": {k: int(len(v)) for k, v in splits.items()},
                          "grade_counts": {k: np.bincount(v.label, minlength=5).tolist() for k, v in splits.items()},
                          "split_method": "stratified, patient-grouped (StratifiedGroupKFold)"},
        "training": {"epochs_run": len(history), "best_epoch": best_epoch, "best_val_qwk": best, "imbalance": args.imbalance,
                     "lr": args.lr, "batch_size": args.batch_size, "pretrained_imagenet": not args.no_pretrained,
                     "device": str(device), "torch": torch.__version__, "python": platform.python_version(), "history": history},
        "evaluation": {"split": "held-out test (never used for training, model selection or calibration)", "test_metrics": test_metrics},
        "clinical_use_status": "NOT CLINICALLY VALIDATED — research/investigational use under clinician supervision only",
        "intended_use": "Assist trained clinicians in screening colour fundus photographs for signs of diabetic retinopathy. Not for autonomous diagnosis.",
        "limitations": [
            "Performance has only been measured on the dataset split above; it may differ on other cameras, populations and image protocols.",
            "Does not detect diseases other than diabetic retinopathy (e.g. glaucoma, AMD, retinal detachment, tumours).",
            "Does not assess diabetic macular oedema separately.",
            "Requires prospective clinical validation in the target Indian population before any clinical claim.",
        ],
    }
    if args.synthetic:
        card["clinical_use_status"] = "SYNTHETIC SMOKE-TEST MODEL — NO CLINICAL MEANING. NEVER USE ON PATIENTS."
    (run / "model_card.json").write_text(json.dumps(card, indent=2))

    dest = Path(args.registry) / MODULE / version
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copy(run / "best.pt", dest / "weights.pt")
    card["weights_sha256"] = file_sha256(dest / "weights.pt")
    (dest / "model_card.json").write_text(json.dumps(card, indent=2))
    for f in ("confusion_matrix.png", "roc_curves.png"):
        if (run / f).exists():
            shutil.copy(run / f, dest / f)
    if not args.no_activate:
        (Path(args.registry) / MODULE / "ACTIVE").write_text(version)
    print(json.dumps({"registered": str(dest), "active": not args.no_activate,
                      "test_accuracy": test_metrics["accuracy"], "test_qwk": test_metrics["quadratic_weighted_kappa"],
                      "referable": test_metrics.get("referable")}, indent=2))
    return dest


if __name__ == "__main__":
    main()
