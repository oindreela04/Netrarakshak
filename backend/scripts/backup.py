"""Backup: database + encrypted object store + model registry into one timestamped archive.

    python scripts/backup.py --out D:\\netrarakshak-backups

PostgreSQL is dumped with pg_dump (must be on PATH); SQLite is copied with the online backup API.
Stored images remain encrypted inside the archive. Keep STORAGE_ENCRYPTION_KEY in a separate secure vault —
an archive without the key cannot be restored, and the key without the archive reveals nothing.
For managed production (RDS/Cloud SQL + S3) prefer provider snapshots + S3 versioning; this script is for
single-server installs and periodic off-site copies.
"""
import argparse
import shutil
import sqlite3
import subprocess
import sys
import tarfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.config import get_settings  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="backups")
    a = ap.parse_args()
    s = get_settings()
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    work = Path(a.out) / f"netrarakshak-{stamp}"
    work.mkdir(parents=True, exist_ok=True)
    if s.is_sqlite:
        src = sqlite3.connect(s.database_url.replace("sqlite:///", ""))
        dst = sqlite3.connect(work / "database.sqlite3")
        src.backup(dst); dst.close(); src.close()
    else:
        url = s.database_url.replace("postgresql+psycopg2://", "postgresql://")
        subprocess.run(["pg_dump", "--format=custom", f"--file={work / 'database.pgdump'}", url], check=True)
    if s.storage_backend == "local" and Path(s.local_storage_dir).exists():
        shutil.copytree(s.local_storage_dir, work / "storage")
    if Path(s.model_registry_dir).exists():
        shutil.copytree(s.model_registry_dir, work / "model_registry")
    archive = Path(a.out) / f"netrarakshak-{stamp}.tar.gz"
    with tarfile.open(archive, "w:gz") as t:
        t.add(work, arcname=work.name)
    shutil.rmtree(work)
    print(f"Backup written: {archive}")


if __name__ == "__main__":
    main()
