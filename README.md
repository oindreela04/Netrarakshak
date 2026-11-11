# NetraRakshak

**See Beyond the Retina. Detect Earlier. Protect Vision.**

AI-assisted, clinician-supervised retinal screening platform for hospitals, eye clinics and diagnostic centres:
patient registration and consent → fundus image upload → automatic image-quality assessment → disease-specific AI
analysis with calibrated confidence and Grad-CAM → ophthalmologist review and signature → hospital-branded PDF report
→ patient history, analytics, multi-hospital SaaS administration.

> **Status: v0.9 pre-release, investigational.** Includes an active diabetic retinopathy model
> (EfficientNet-B0 v2026.11.11-1219, trained on APTOS 2019; held-out referable-DR sensitivity 82.0%, specificity
> 96.6%; see `docs/regulatory/05_model_evaluation.md`). It is a clinician-supervised aid: NetraRakshak is not
> clinically validated and not approved by CDSCO or any regulator, and APTOS commercial-use terms are unconfirmed.

## Requirements (Windows 10/11)
- Python 3.11, 3.12 or 3.13 (python.org installer, tick *Add python.exe to PATH*)
- Node.js 20 LTS or newer
- Optional: PostgreSQL 15+ (SQLite is used automatically for local development)
- Optional for training: NVIDIA GPU + CUDA build of PyTorch

## Install and run (PowerShell, from the project folder)

```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1     # one time: venv, packages, .env with fresh secrets, demo data
powershell -ExecutionPolicy Bypass -File .\start.ps1     # opens API + web app, then http://localhost:3000
```

Manual equivalent:

```powershell
cd backend
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env        # then set JWT_SECRET and STORAGE_ENCRYPTION_KEY
python scripts\seed.py
uvicorn app.main:app --port 8000 --reload
# second terminal
cd frontend
copy .env.example .env.local
npm install
npm run dev
```

- Web app: http://localhost:3000 · API docs: http://localhost:8000/api/docs
- Demo accounts (password `Demo@NetraRakshak2026`, development only):
  `admin@aarogya.example`, `doctor@aarogya.example`, `tech@aarogya.example`, `reception@aarogya.example`,
  a second tenant `admin@sunrise.example`, and the platform operator `superadmin@netrarakshak.in`.
  All demo patients are labelled **SYNTHETIC**.

## Tests

```powershell
powershell -ExecutionPolicy Bypass -File .\run-tests.ps1   # pytest (30 tests) + TypeScript check + production build
```

## Training the DR model with your Kaggle account

**Option A — your Windows PC** (best with an NVIDIA GPU): accept the APTOS 2019 competition rules on kaggle.com,
save your API token to `%USERPROFILE%\.kaggle\kaggle.json`, then run
`powershell -ExecutionPolicy Bypass -File .\train-dr-aptos.ps1`. It downloads the data with your account, trains,
calibrates, evaluates on a held-out split and activates the model. Restart the API afterwards.

**Option B — a Kaggle Notebook** (free GPU, nothing downloaded to your PC): follow the steps at the top of
`tools/kaggle_notebook_train.py`, uploading `netrarakshak-ai-training.zip` as a private Kaggle dataset; download the
resulting `netrarakshak_model_registry.zip` and unzip it into `backend/ai/model_registry`.

### Manual training
1. Obtain a labelled fundus dataset you are licensed to use (see `docs/datasets.md` — APTOS/EyePACS terms must be
   checked for commercial use).
2. Train, calibrate, evaluate and register:
   ```powershell
   cd backend; .\.venv\Scripts\Activate.ps1
   python -m ai.modules.diabetic_retinopathy.train --labels D:\aptos\train.csv --images D:\aptos\train_images `
     --dataset-name "APTOS 2019" --dataset-licence "<terms>" --arch efficientnet_b0 --size 384 --epochs 25
   ```
3. Restart the API. *AI modules* in the app shows the model card with the computed held-out metrics.

## Project layout
```
backend/   FastAPI app (app/), AI pipeline (ai/), scripts (seed, backup, restore, retention), tests/
frontend/  Next.js public website + authenticated application
tools/     capture_agent.py — fundus-camera folder-watch uploader (reference camera integration)
docs/      architecture, datasets, deployment, regulatory/ (intended use, risk, SRS, validation plan, …)
deploy/    Procfile, render.yaml examples
```

See `PROJECT_STATUS.md` for what is complete and what is outstanding.
