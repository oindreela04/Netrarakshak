"""Create a SYNTHETIC labelled dataset for pipeline smoke tests (no clinical meaning).

    python scripts/make_synthetic_dataset.py --out data/synthetic_ds --n 100
"""
import argparse
import sys
from pathlib import Path

import cv2
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.services.synthetic_fundus import make_synthetic_fundus  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/synthetic_ds")
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--size", type=int, default=512)
    a = ap.parse_args()
    out = Path(a.out); (out / "images").mkdir(parents=True, exist_ok=True)
    rows = []
    for i in range(a.n):
        grade = i % 5
        img = make_synthetic_fundus(a.size, seed=1000 + i, lesions=grade * 12, eye="right" if i % 2 else "left")
        name = f"SYNTHETIC_{i:04d}.png"
        cv2.imwrite(str(out / "images" / name), img)
        rows.append({"image_path": name, "label": grade, "patient_id": f"SYN{i // 2:04d}"})
    pd.DataFrame(rows).to_csv(out / "labels.csv", index=False)
    print(f"wrote {a.n} SYNTHETIC images to {out}")


if __name__ == "__main__":
    main()
