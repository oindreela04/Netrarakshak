# Deploy the Streamlit demo (free, Streamlit Community Cloud)

The Streamlit edition (`streamlit_app.py`) runs the real NetraRakshak backend in-process: quality checks, the trained
DR model with Grad-CAM, clinician signing and PDF reports. Demo data is kept in a temporary database that resets when
the app restarts. **Use synthetic or properly consented test images only.**

## Files that must be in your GitHub repository
- `streamlit_app.py` (repository root)
- `requirements.txt` (repository root — Streamlit installs from this)
- `.streamlit/config.toml` (light theme; optional but recommended)
- `backend/` (including `backend/ai/model_registry/diabetic_retinopathy/2026.11.11-1219/weights.pt`)

GitHub's web uploader skips folders that start with a dot. Create the theme file with **Add file → Create new file**,
type `.streamlit/config.toml` as the name, paste its contents and commit.

## Deploy
1. Go to https://share.streamlit.io and sign in with GitHub.
2. **Create app → Deploy a public app from GitHub.**
3. Repository: `oindreela04/Netrarakshak`, Branch: `main`, Main file path: `streamlit_app.py`.
4. **Advanced settings → Python version: 3.12.** (Optional secret: `SEED_PASSWORD = "<your demo password>"`.)
5. **Deploy.** The first build installs PyTorch and takes several minutes.

The app sleeps after 12 hours without visitors; anyone opening it can wake it.
