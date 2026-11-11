# Deploy NetraRakshak: website on Vercel, API + AI on Render

**Use this deployment only for demonstrations with SYNTHETIC data** until the regulatory, validation and
data-protection steps in `PROJECT_STATUS.md` are complete. Do not upload real patient images to a demo.

Vercel hosts the Next.js website. The FastAPI backend, PyTorch model and PostgreSQL database run on Render, because
PyTorch and the model are far larger than Vercel's serverless function limit. Both deploy from one GitHub repository.

## 1. Put the code on GitHub (once)
1. Create a **private** repository on github.com, e.g. `netrarakshak` (no README, no .gitignore).
2. In PowerShell inside the project folder (the zip already contains a Git repository with one commit):
   ```powershell
   git remote add origin https://github.com/<your-username>/netrarakshak.git
   git branch -M main
   git push -u origin main
   ```
   (Install Git for Windows from https://git-scm.com if `git` is not found. The trained model, 16 MB, is included.)

## 2. Backend on Render
1. Generate a storage encryption key and keep a copy in a password manager (without it, stored images cannot be decrypted):
   ```powershell
   cd backend; .\.venv\Scripts\python.exe -c "from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())"
   ```
2. render.com → **New → Blueprint** → connect GitHub → pick the repository. Render reads `render.yaml` and proposes:
   `netrarakshak-api` (web service with a 5 GB disk) and `netrarakshak-db` (PostgreSQL).
3. Fill the variables Render asks for:
   - `STORAGE_ENCRYPTION_KEY` — the key from step 1
   - `CORS_ORIGINS` — leave as `https://example.com` for now; you will set it after step 3
   - `SEED_PASSWORD` — a private password for the demo accounts (at least 10 characters with upper/lower case, digit, symbol)
4. Click **Apply**. The first build installs PyTorch and takes several minutes. When it is live, open
   `https://<your-api>.onrender.com/api/health` — it should show `{"status":"ok",...}`. Copy the API URL.

Plan: PyTorch inference needs about 1–2 GB RAM; the blueprint requests the *Standard* instance. Smaller instances may run
out of memory when the model loads.

## 3. Website on Vercel
1. vercel.com → **Add New → Project** → import the same GitHub repository.
2. **Root Directory:** `frontend` (Framework preset: Next.js is detected automatically).
3. **Environment Variables:** `NEXT_PUBLIC_API_URL` = your Render API URL (no trailing slash).
4. **Deploy.** Copy the site URL, e.g. `https://netrarakshak.vercel.app`.

## 4. Connect the two
On Render → `netrarakshak-api` → **Environment** → set `CORS_ORIGINS` to the Vercel URL → **Save** (the API restarts).
If you later add a custom domain on Vercel, add it to `CORS_ORIGINS` too (comma-separated) and redeploy Vercel so the
browser security policy includes the API URL.

## 5. Check
Open the Vercel URL → **Sign in** with `admin@aarogya.example` and your `SEED_PASSWORD` → AI modules should show the
diabetic retinopathy model as Active. Then sign in as `superadmin@netrarakshak.in` and change its password in
Account settings.

## Updating
Push to `main`: Vercel and Render both redeploy automatically.

## Troubleshooting
| Symptom | Fix |
|---|---|
| Sign-in shows "Failed to fetch" | `CORS_ORIGINS` on Render must exactly match the Vercel URL (https, no trailing slash) |
| Render build fails on torch | Check the build uses `requirements-deploy.txt` (CPU wheels) |
| API restarts while analysing | Instance is out of memory — use a plan with at least 2 GB RAM |
| "Refusing to create demo accounts" in logs | Set `SEED_PASSWORD` on Render, or set `SEED_DEMO=false` |
| Images missing after a redeploy | The disk must be attached at `/var/data` (from `render.yaml`) |
