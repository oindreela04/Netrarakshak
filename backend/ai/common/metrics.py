"""Evaluation metrics computed from real predictions. Nothing here is ever hand-entered."""
import numpy as np
from sklearn.metrics import (accuracy_score, cohen_kappa_score, confusion_matrix, f1_score,
                             precision_recall_fscore_support, roc_auc_score)


def _safe_auc(y_true, scores, **kw):
    try:
        return float(roc_auc_score(y_true, scores, **kw))
    except ValueError:
        return None  # e.g. a class absent from the test split


def multiclass_metrics(y_true: np.ndarray, probs: np.ndarray, class_names: list[str],
                       referable_from: int | None = None) -> dict:
    """Full metric set for an ordinal multi-class grader.

    referable_from: index of the first "referable" class. For DR (ICDR scale) moderate NPDR (2) and above is
    the conventional referable threshold; binary sensitivity/specificity are reported at that cut-off.
    """
    y_pred = probs.argmax(1)
    k = len(class_names)
    prec, rec, f1, sup = precision_recall_fscore_support(y_true, y_pred, labels=list(range(k)), zero_division=0)
    cm = confusion_matrix(y_true, y_pred, labels=list(range(k)))
    per_class = {}
    for i, name in enumerate(class_names):
        tp = cm[i, i]
        fn = cm[i].sum() - tp
        fp = cm[:, i].sum() - tp
        tn = cm.sum() - tp - fn - fp
        per_class[name] = {
            "precision": float(prec[i]), "recall_sensitivity": float(rec[i]), "f1": float(f1[i]),
            "specificity": float(tn / (tn + fp)) if (tn + fp) else None, "support": int(sup[i]),
            "roc_auc_ovr": _safe_auc((y_true == i).astype(int), probs[:, i]),
        }
    out = {
        "n": int(len(y_true)),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "macro_precision": float(prec.mean()), "macro_recall": float(rec.mean()),
        "macro_f1": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "weighted_f1": float(f1_score(y_true, y_pred, average="weighted", zero_division=0)),
        "quadratic_weighted_kappa": float(cohen_kappa_score(y_true, y_pred, weights="quadratic")),
        "roc_auc_macro_ovr": _safe_auc(y_true, probs, multi_class="ovr", average="macro", labels=list(range(k))),
        "confusion_matrix": cm.tolist(), "class_names": class_names, "per_class": per_class,
    }
    if referable_from is not None:
        yb = (y_true >= referable_from).astype(int)
        pb = probs[:, referable_from:].sum(1)
        pred_b = (y_pred >= referable_from).astype(int)
        tp = int(((yb == 1) & (pred_b == 1)).sum()); fn = int(((yb == 1) & (pred_b == 0)).sum())
        tn = int(((yb == 0) & (pred_b == 0)).sum()); fp = int(((yb == 0) & (pred_b == 1)).sum())
        out["referable"] = {
            "definition": f"class index >= {referable_from} ({class_names[referable_from]} or worse)",
            "sensitivity": tp / (tp + fn) if (tp + fn) else None,
            "specificity": tn / (tn + fp) if (tn + fp) else None,
            "ppv": tp / (tp + fp) if (tp + fp) else None, "npv": tn / (tn + fn) if (tn + fn) else None,
            "roc_auc": _safe_auc(yb, pb), "confusion": {"tp": tp, "fn": fn, "tn": tn, "fp": fp},
        }
    return out


def expected_calibration_error(probs: np.ndarray, y_true: np.ndarray, bins: int = 15) -> float:
    conf = probs.max(1)
    correct = (probs.argmax(1) == y_true).astype(float)
    edges = np.linspace(0, 1, bins + 1)
    ece = 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (conf > lo) & (conf <= hi)
        if m.any():
            ece += m.mean() * abs(correct[m].mean() - conf[m].mean())
    return float(ece)
