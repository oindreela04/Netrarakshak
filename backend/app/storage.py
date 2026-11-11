"""Private object storage with application-level encryption at rest (Fernet / AES-128-CBC + HMAC-SHA256).

Backends:
  * local — encrypted blobs on the server's disk (development / single-server installs)
  * s3    — any private S3-compatible bucket (AWS S3 ap-south-1, MinIO, Wasabi, ...). Objects are encrypted
            client-side AND stored with server-side encryption; the bucket must block all public access.
"""
import hashlib
import os
import re
from pathlib import Path

from cryptography.fernet import Fernet

from .config import BACKEND_DIR, get_settings

settings = get_settings()
_KEY_RE = re.compile(r"^[A-Za-z0-9/_.\-]+$")


def _load_key() -> bytes:
    if settings.storage_encryption_key:
        return settings.storage_encryption_key.encode()
    if settings.environment == "production":
        raise RuntimeError("STORAGE_ENCRYPTION_KEY is required in production")
    key_file = BACKEND_DIR / "data" / ".dev_storage_key"
    key_file.parent.mkdir(parents=True, exist_ok=True)
    if not key_file.exists():
        key_file.write_bytes(Fernet.generate_key())
    return key_file.read_bytes().strip()


class Storage:
    def __init__(self):
        self.fernet = Fernet(_load_key())

    @staticmethod
    def _check(key: str):
        if not _KEY_RE.match(key) or ".." in key:
            raise ValueError("invalid storage key")

    def put(self, key: str, data: bytes) -> str:
        self._check(key)
        self._write(key, self.fernet.encrypt(data))
        return hashlib.sha256(data).hexdigest()

    def get(self, key: str) -> bytes:
        self._check(key)
        return self.fernet.decrypt(self._read(key))

    def delete(self, key: str) -> None:
        self._check(key)
        self._remove(key)


class LocalStorage(Storage):
    def __init__(self, root: str):
        super().__init__()
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        return self.root / key

    def _write(self, key, blob):
        p = self._path(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(p.suffix + ".tmp")
        tmp.write_bytes(blob)
        os.replace(tmp, p)

    def _read(self, key):
        return self._path(key).read_bytes()

    def _remove(self, key):
        p = self._path(key)
        if p.exists():
            # Secure deletion: overwrite ciphertext before unlinking (best effort on SSD/journaling FS;
            # the real guarantee is crypto-shredding by rotating STORAGE_ENCRYPTION_KEY).
            size = p.stat().st_size
            with open(p, "r+b") as f:
                f.write(os.urandom(size))
                f.flush()
                os.fsync(f.fileno())
            p.unlink()


class S3Storage(Storage):
    def __init__(self):
        super().__init__()
        import boto3
        self.bucket = settings.s3_bucket
        self.client = boto3.client(
            "s3", endpoint_url=settings.s3_endpoint_url or None, region_name=settings.s3_region,
            aws_access_key_id=settings.s3_access_key_id or None, aws_secret_access_key=settings.s3_secret_access_key or None)

    def _write(self, key, blob):
        self.client.put_object(Bucket=self.bucket, Key=key, Body=blob, ServerSideEncryption="AES256",
                               ContentType="application/octet-stream")

    def _read(self, key):
        return self.client.get_object(Bucket=self.bucket, Key=key)["Body"].read()

    def _remove(self, key):
        self.client.delete_object(Bucket=self.bucket, Key=key)


_storage: Storage | None = None


def get_storage() -> Storage:
    global _storage
    if _storage is None:
        _storage = S3Storage() if settings.storage_backend == "s3" else LocalStorage(settings.local_storage_dir)
    return _storage
