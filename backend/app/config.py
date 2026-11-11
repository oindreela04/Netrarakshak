"""Central configuration. All secrets come from environment variables / .env — never hardcoded."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "NetraRakshak"
    environment: str = "development"  # development | staging | production

    # Database: PostgreSQL in production. SQLite is allowed ONLY for local development / tests.
    database_url: str = f"sqlite:///{(BACKEND_DIR / 'data' / 'netrarakshak_dev.db').as_posix()}"

    # Auth
    jwt_secret: str = "CHANGE_ME_DEV_ONLY_SECRET_please_override_in_env_0123456789"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 30
    refresh_token_days: int = 7
    max_failed_logins: int = 5
    lockout_minutes: int = 15

    # Storage: "local" (encrypted files on disk) or "s3" (private S3-compatible bucket, SSE + client-side encryption)
    storage_backend: str = "local"
    local_storage_dir: str = str(BACKEND_DIR / "data" / "storage")
    storage_encryption_key: str = ""  # Fernet key. Generated automatically in development if empty.
    s3_endpoint_url: str = ""
    s3_bucket: str = ""
    s3_region: str = "ap-south-1"
    s3_access_key_id: str = ""
    s3_secret_access_key: str = ""

    # AI
    model_registry_dir: str = str(BACKEND_DIR / "ai" / "model_registry")
    # Models trained on synthetic data (CI smoke tests) are never loaded unless this is explicitly true.
    allow_nonclinical_test_models: bool = False
    uncertainty_confidence_threshold: float = 0.60
    uncertainty_entropy_threshold: float = 0.75  # normalised entropy (0..1)

    # Upload limits
    max_upload_mb: int = 40
    min_image_side_px: int = 512

    # CORS
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # Data retention (days) — configurable per hospital, this is the platform default
    default_retention_days: int = 365 * 7

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    # Hosts (Render, Heroku, Railway) hand out postgres:// or postgresql:// URLs without a driver; pin psycopg2,
    # which is what requirements.txt installs (SQLAlchemy 2.1 would otherwise look for psycopg 3).
    for prefix in ("postgres://", "postgresql://"):
        if s.database_url.startswith(prefix):
            s.database_url = "postgresql+psycopg2://" + s.database_url[len(prefix):]
    for attr in ("model_registry_dir", "local_storage_dir"):
        p = Path(getattr(s, attr))
        if not p.is_absolute():
            setattr(s, attr, str(BACKEND_DIR / p))
    if s.environment == "production":
        if "CHANGE_ME" in s.jwt_secret or len(s.jwt_secret) < 32:
            raise RuntimeError("JWT_SECRET must be set to a strong value in production")
        if s.is_sqlite:
            raise RuntimeError("SQLite is not permitted in production; set DATABASE_URL to PostgreSQL")
        if not s.storage_encryption_key:
            raise RuntimeError("STORAGE_ENCRYPTION_KEY must be set in production")
        if s.allow_nonclinical_test_models:
            raise RuntimeError("ALLOW_NONCLINICAL_TEST_MODELS must be false in production")
    return s
