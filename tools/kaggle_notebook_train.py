"""Train the NetraRakshak DR model inside a Kaggle Notebook (free GPU; the dataset never leaves Kaggle).

1. On kaggle.com accept the rules of "aptos2019-blindness-detection".
2. Create a private Kaggle Dataset by uploading `netrarakshak-ai-training.zip` (contains backend/ai).
3. New Notebook → Settings: Accelerator = GPU, Internet = On (for ImageNet weights).
   Add Input: the competition "APTOS 2019 Blindness Detection" and your private code dataset.
4. Paste this file into a cell and run it (about 1–2 hours on a T4/P100).
5. Download /kaggle/working/netrarakshak_model_registry.zip from the Output tab and unzip it into
   backend/ai/model_registry on your server/PC, then restart the API.
"""
import shutil
import subprocess
import sys
from pathlib import Path

inp = Path("/kaggle/input")
labels = next(inp.rglob("aptos*/train.csv"), None) or next(p for p in inp.rglob("train.csv") if (p.parent / "train_images").exists())
code_ai = next(p for p in inp.rglob("ai") if (p / "modules" / "diabetic_retinopathy" / "train.py").exists())
work = Path("/kaggle/working")
src = work / "src"
if src.exists():
    shutil.rmtree(src)
shutil.copytree(code_ai, src / "ai")
print("labels:", labels, "\ncode:", code_ai)

cmd = [sys.executable, "-u", "-m", "ai.modules.diabetic_retinopathy.train",
       "--labels", str(labels), "--images", str(labels.parent / "train_images"), "--format", "aptos",
       "--dataset-name", "APTOS 2019 Blindness Detection (Kaggle)",
       "--dataset-licence", "Kaggle competition rules accepted by the account holder; commercial use NOT confirmed",
       "--arch", "efficientnet_b0", "--size", "384", "--epochs", "25", "--batch-size", "24", "--workers", "4",
       "--work-dir", str(work / "runs"), "--registry", str(work / "model_registry"), "--cache-dir", str(work / "cache")]
proc = subprocess.Popen(cmd, cwd=src, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
for line in proc.stdout:  # stream progress into the notebook cell
    print(line, end="", flush=True)
if proc.wait() != 0:
    raise SystemExit("Training failed - copy the last lines above and send them to Claude.")
shutil.make_archive(str(work / "netrarakshak_model_registry"), "zip", work / "model_registry")
print("Done: download netrarakshak_model_registry.zip from the Output tab.")
