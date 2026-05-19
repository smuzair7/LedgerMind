"""File storage abstraction.

Production: MinIO (S3-compatible) via aioboto3.
Dev / no-Docker: local disk under {data_dir}/files/.

Both backends expose the same async surface so callers don't branch.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Protocol

import aiofiles
from fastapi import UploadFile

from app.settings import get_infra, get_settings


class FileStorage(Protocol):
    async def put(self, key: str, file: UploadFile) -> str: ...
    async def get_path(self, key: str) -> Path: ...
    async def delete_prefix(self, prefix: str) -> None: ...


class LocalFileStorage:
    """Disk-backed storage. The default in dev and the no-S3 path in prod."""

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, key: str) -> Path:
        p = (self.root / key).resolve()
        # Defense in depth: prevent path traversal.
        if not str(p).startswith(str(self.root.resolve())):
            raise ValueError("invalid key")
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    async def put(self, key: str, file: UploadFile) -> str:
        path = self._resolve(key)
        async with aiofiles.open(path, "wb") as f:
            while chunk := await file.read(1024 * 1024):
                await f.write(chunk)
        return key

    async def get_path(self, key: str) -> Path:
        return self._resolve(key)

    async def delete_prefix(self, prefix: str) -> None:
        target = (self.root / prefix).resolve()
        if not str(target).startswith(str(self.root.resolve())):
            return
        if target.exists():
            shutil.rmtree(target, ignore_errors=True)


def get_storage() -> FileStorage:
    """Pick MinIO when S3 env is set, otherwise local disk."""
    infra = get_infra()
    if infra.s3_endpoint and infra.s3_access_key:
        # Lazy import — aioboto3 has a big import cost.
        from app.storage.s3 import S3FileStorage  # noqa: PLC0415

        return S3FileStorage()
    return LocalFileStorage(Path(get_settings().data_dir) / "files")
