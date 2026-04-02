# LogRaven — Storage Backend Abstraction
#
# LocalStorageBackend: development — files under LOCAL_STORAGE_PATH (downloads via signed /api/v1/downloads/file)
# S3StorageBackend: production — boto3 upload/download/presign

from __future__ import annotations

import asyncio
import hashlib
import os
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path

import aiofiles

from app.config import settings
from app.utils.storage_paths import resolved_file_under_storage_base


class StorageBackend(ABC):

    @abstractmethod
    async def save_file(self, file_obj, key: str) -> str:
        """Save a file. Returns the storage key."""
        pass

    @abstractmethod
    async def get_file_path(self, key: str) -> Path:
        """Get local file path (for workers to read files)."""
        pass

    @abstractmethod
    def get_download_url(self, key: str) -> str:
        """Get URL for file download."""
        pass

    @abstractmethod
    async def delete_file(self, key: str) -> None:
        pass

    async def save_file_from_bytes(self, key: str, data: bytes) -> str:
        """Save raw bytes (e.g. generated PDF)."""
        raise NotImplementedError


class LocalStorageBackend(StorageBackend):
    """Development storage. Public URLs use signed download tokens (no open /files/ mount)."""

    def __init__(self, base_path: str = "./local", public_base_url: str | None = None):
        self.base = Path(base_path)
        self.base.mkdir(parents=True, exist_ok=True)
        self._public_base = (public_base_url or "http://localhost:8000").rstrip("/")

    async def save_file(self, file_obj, key: str) -> str:
        dest = self.base / key
        dest.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(dest, "wb") as f:
            while chunk := await file_obj.read(1024 * 1024):
                await f.write(chunk)
        return key

    async def get_file_path(self, key: str) -> Path:
        return resolved_file_under_storage_base(self.base, key)

    def get_download_url(self, key: str) -> str:
        raise RuntimeError("Local storage downloads must use signed download tokens.")

    async def delete_file(self, key: str) -> None:
        path = resolved_file_under_storage_base(self.base, key)
        if path.exists():
            path.unlink()

    async def save_file_from_bytes(self, key: str, data: bytes) -> str:
        dest = self.base / key
        dest.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(dest, "wb") as f:
            await f.write(data)
        return key


class S3StorageBackend(StorageBackend):
    """Production storage using AWS S3 (or S3-compatible API via AWS_ENDPOINT_URL)."""

    def __init__(
        self,
        bucket: str,
        region: str = "eu-west-1",
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
        endpoint_url: str | None = None,
    ):
        import boto3

        self.bucket = bucket
        self.region = region
        self._temp_root = Path(tempfile.gettempdir()) / "lograven_s3"
        self._temp_root.mkdir(parents=True, exist_ok=True)

        kwargs: dict = {"region_name": region}
        if aws_access_key_id and aws_secret_access_key:
            kwargs["aws_access_key_id"] = aws_access_key_id
            kwargs["aws_secret_access_key"] = aws_secret_access_key
        if endpoint_url:
            kwargs["endpoint_url"] = endpoint_url

        self._client = boto3.client("s3", **kwargs)

    async def _run_sync(self, call):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, call)

    async def save_file(self, file_obj, key: str) -> str:
        fd, path = tempfile.mkstemp(suffix=".upload")
        try:
            with os.fdopen(fd, "wb") as tmp:
                while chunk := await file_obj.read(1024 * 1024):
                    tmp.write(chunk)
            await self._run_sync(lambda: self._client.upload_file(path, self.bucket, key))
        finally:
            Path(path).unlink(missing_ok=True)
        return key

    async def get_file_path(self, key: str) -> Path:
        h = hashlib.sha256(key.encode()).hexdigest()[:16]
        safe_name = Path(key).name.replace("/", "_")[:200]
        dest = self._temp_root / f"{h}_{safe_name}"
        await self._run_sync(
            lambda: self._client.download_file(self.bucket, key, str(dest)),
        )
        return dest

    def get_download_url(self, key: str) -> str:
        return self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=settings.S3_DOWNLOAD_URL_EXPIRE_SECONDS,
        )

    async def delete_file(self, key: str) -> None:
        await self._run_sync(lambda: self._client.delete_object(Bucket=self.bucket, Key=key))

    async def save_file_from_bytes(self, key: str, data: bytes) -> str:
        await self._run_sync(
            lambda: self._client.put_object(Bucket=self.bucket, Key=key, Body=data),
        )
        return key


def create_storage_backend():
    """Single factory used by FastAPI deps and Celery pipeline."""
    if settings.STORAGE_BACKEND == "s3":
        return S3StorageBackend(
            bucket=settings.S3_BUCKET_NAME,
            region=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID or None,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY or None,
            endpoint_url=settings.S3_ENDPOINT_URL or None,
        )
    return LocalStorageBackend(
        base_path=settings.LOCAL_STORAGE_PATH,
        public_base_url=settings.PUBLIC_API_BASE_URL,
    )
