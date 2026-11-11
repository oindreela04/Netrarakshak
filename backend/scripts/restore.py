"""Restore a backup produced by scripts/backup.py into the CURRENT configuration (stop the API first).

    python scripts/restore.py D:\\netrarakshak-backups\\netrarakshak-20261111-101500.tar.gz --yes
"""
import argparse
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.config import get_settings  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("archive")
    ap.add_argument("--yes", action="store_true", help="confirm overwrite of the current data")
    a = ap.parse_args()
    if not a.yes:
        sys.exit("Refusing to overwrite data without --yes")
    s = get_settings()
    with tempfile.TemporaryDirectory() as tmp:
        with tarfile.open(a.archive) as t:
            t.extractall(tmp, filter="data")
        root = next(Path(tmp).iterdir())
        if (root / "database.sqlite3").exists():
            if not s.is_sqlite:
                sys.exit("Backup is SQLite but DATABASE_URL is PostgreSQL")
            shutil.copy(root / "database.sqlite3", s.database_url.replace("sqlite:///", ""))
        else:
            url = s.database_url.replace("postgresql+psycopg2://", "postgresql://")
            subprocess.run(["pg_restore", "--clean", "--if-exists", "--no-owner", f"--dbname={url}", str(root / "database.pgdump")], check=True)
        if (root / "storage").exists():
            shutil.rmtree(s.local_storage_dir, ignore_errors=True)
            shutil.copytree(root / "storage", s.local_storage_dir)
        if (root / "model_registry").exists():
            shutil.rmtree(s.model_registry_dir, ignore_errors=True)
            shutil.copytree(root / "model_registry", s.model_registry_dir)
    print("Restore complete. Ensure STORAGE_ENCRYPTION_KEY matches the key used when the backup was taken.")


if __name__ == "__main__":
    main()
