"""Evaluate a registered DR model on an EXTERNAL labelled dataset (e.g. IDRiD, Messidor-2, a local clinical set).

    python -m ai.modules.diabetic_retinopathy.evaluate --version 2026.11.20-1030 ^
        --labels D:\\data\\idrid\\labels.csv --images D:\\data\\idrid\\images --format generic --name "IDRiD test"

Results are appended to the version folder as external_evaluations.json (computed, never typed in).
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import torch
from torch.utils.data import DataLoader

from ai.common.metrics import expected_calibration_error, multiclass_metrics
from ai.modules.diabetic_retinopathy.dataset import FundusDataset, load_labels
from ai.modules.diabetic_retinopathy.model import CLASS_NAMES, REFERABLE_FROM, build_model


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", required=True)
    ap.add_argument("--labels", required=True)
    ap.add_argument("--images", required=True)
    ap.add_argument("--format", default="auto")
    ap.add_argument("--name", required=True)
    ap.add_argument("--registry", default="ai/model_registry")
    ap.add_argument("--batch-size", type=int, default=16)
    a = ap.parse_args(argv)

    vdir = Path(a.registry) / "diabetic_retinopathy" / a.version
    card = json.loads((vdir / "model_card.json").read_text())
    model = build_model(card["architecture"], pretrained=False)
    model.load_state_dict(torch.load(vdir / "weights.pt", map_location="cpu", weights_only=True))
    model.eval()
    df = load_labels(a.labels, a.images, a.format)
    dl = DataLoader(FundusDataset(df, card["input_size"], train=False), batch_size=a.batch_size)
    logits, ys = [], []
    with torch.no_grad():
        for x, y in dl:
            logits.append(model(x)); ys.append(y)
    probs = torch.softmax(torch.cat(logits) / card["temperature"], 1).numpy()
    y = torch.cat(ys).numpy()
    m = multiclass_metrics(y, probs, CLASS_NAMES, REFERABLE_FROM)
    m["ece"] = expected_calibration_error(probs, y)
    path = vdir / "external_evaluations.json"
    hist = json.loads(path.read_text()) if path.exists() else []
    hist.append({"dataset": a.name, "evaluated_at": datetime.now(timezone.utc).isoformat(), "metrics": m})
    path.write_text(json.dumps(hist, indent=2))
    print(json.dumps({k: m[k] for k in ("n", "accuracy", "macro_f1", "quadratic_weighted_kappa", "roc_auc_macro_ovr")}, indent=2))
    print(json.dumps(m.get("referable"), indent=2))


if __name__ == "__main__":
    main()
