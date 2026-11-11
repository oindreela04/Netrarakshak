# Deployment

## Topology (production)

| Layer | Recommendation |
|---|---|
| Frontend | Vercel (`frontend/`, region `bom1`), env `NEXT_PUBLIC_API_URL=https://api.<your-domain>` |
| API + inference | Managed containers/VMs in an Indian region (AWS ap-south-1 / Azure Central India / GCP asia-south1). GPU optional: CPU inference of EfficientNet-B0 at 384 px is typically sub-second; use a GPU node for training. |
| Database | Managed PostgreSQL 15+ with encryption at rest, automated backups, PITR, private networking |
| Object storage | Private S3 bucket (Block Public Access ON, SSE, versioning, lifecycle for deleted versions) |
| Secrets | Provider secret manager → environment variables (`JWT_SECRET`, `STORAGE_ENCRYPTION_KEY`, DB/S3 credentials) |
| TLS | Managed certificates; HSTS is sent by the API when `ENVIRONMENT=production` |

## Steps

1. Provision PostgreSQL and the S3 bucket; create a least-privilege IAM user restricted to the bucket.
2. Deploy `backend/` with `deploy/Procfile` or `deploy/render.yaml`; set env vars from `backend/.env.example`
   (`ENVIRONMENT=production` refuses to start with SQLite, a weak JWT secret, no storage key, or synthetic models allowed).
3. Run once: `python scripts/seed.py --no-demo` (plans + platform super-admin). Change the super-admin password immediately.
4. Copy a trained, evaluated model version into `MODEL_REGISTRY_DIR` (persistent volume or image layer) and write `ACTIVE`.
5. Deploy `frontend/` to Vercel; set `CORS_ORIGINS` on the API to the Vercel domain.
6. Onboard hospitals from the Platform console.

Schema changes: the API creates tables on start-up (`create_all`). Before the first production release, introduce
Alembic migrations (listed in PROJECT_STATUS as outstanding) so later schema changes are versioned.
