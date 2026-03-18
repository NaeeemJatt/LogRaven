# LogRaven — Storage Backend Abstraction
#
# PURPOSE:
#   Provides a unified file storage interface with two implementations:
#   - LocalStorageBackend: saves files to ./local/ folder (development)
#   - S3StorageBackend: saves files to AWS S3 (production)
#
# SWITCHING BETWEEN BACKENDS:
#   Set STORAGE_BACKEND="local" for development (default)
#   Set STORAGE_BACKEND="s3" for production
#   Nothing else changes — all file operations go through this abstraction.
#
# CRITICAL RULE: Never use direct file operations anywhere in the codebase.
#   Always use storage.save_file(), storage.get_download_url(), etc.
#
# LOCAL STORAGE SERVING:
#   In development, FastAPI serves local/ at /files/ via StaticFiles mount.
#   get_download_url() returns http://localhost:8000/files/{key}
#
# S3 PRODUCTION:
#   S3StorageBackend stub is here for reference.
#   Full implementation added in requirements.prod.txt with boto3.
#
# TODO Month 1 Week 1: Implement LocalStorageBackend.

from abc import ABC, abstractmethod
from pathlib import Path
import aiofiles


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
        """Delete a file."""
        pass


class LocalStorageBackend(StorageBackend):
    """
    Development storage backend. Saves files to local filesystem.
    Files served by FastAPI StaticFiles mount at /files/
    """

    def __init__(self, base_path: str = "./local"):
        self.base = Path(base_path)
        self.base.mkdir(parents=True, exist_ok=True)

    async def save_file(self, file_obj, key: str) -> str:
        dest = self.base / key
        dest.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(dest, "wb") as f:
            while chunk := await file_obj.read(1024 * 1024):  # 1MB chunks
                await f.write(chunk)
        return key

    async def get_file_path(self, key: str) -> Path:
        return self.base / key

    def get_download_url(self, key: str) -> str:
        return f"http://localhost:8000/files/{key}"

    async def delete_file(self, key: str) -> None:
        path = self.base / key
        if path.exists():
            path.unlink()

    async def save_file_from_bytes(self, key: str, data: bytes) -> str:
        """Save raw bytes directly (used by report uploader)."""
        dest = self.base / key
        dest.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(dest, "wb") as f:
            await f.write(data)
        return key


class S3StorageBackend(StorageBackend):
    """
    Production storage backend. Saves files to AWS S3.
    Requires boto3 (in requirements.prod.txt only).
    Full implementation added when STORAGE_BACKEND=s3.
    """

    def __init__(self, bucket: str, region: str = "eu-west-1"):
        self.bucket = bucket
        self.region = region
        # boto3 imported here to avoid ImportError in dev (not in requirements.txt)
        # import boto3
        # self.client = boto3.client("s3", region_name=region)

    async def save_file(self, file_obj, key: str) -> str:
        # TODO: Implement S3 multipart upload for large files
        raise NotImplementedError("S3StorageBackend not yet implemented for production")

    async def get_file_path(self, key: str) -> Path:
        # TODO: Download from S3 to temp path
        raise NotImplementedError

    def get_download_url(self, key: str) -> str:
        # TODO: Generate pre-signed URL valid for 24 hours
        raise NotImplementedError

    async def delete_file(self, key: str) -> None:
        # TODO: Delete object from S3
        raise NotImplementedError
