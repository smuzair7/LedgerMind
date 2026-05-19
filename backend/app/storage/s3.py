"""MinIO / S3 file storage. Lazily imported by storage.files.get_storage()."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import aioboto3
from fastapi import UploadFile

from app.settings import get_infra, get_settings


class S3FileStorage:
    def __init__(self) -> None:
        infra = get_infra()
        self.bucket = infra.s3_bucket
        self._session_kwargs: dict[str, Any] = {
            "aws_access_key_id": infra.s3_access_key,
            "aws_secret_access_key": infra.s3_secret_key,
            "region_name": infra.s3_region,
        }
        self._endpoint = infra.s3_endpoint
        self._cache_root = Path(get_settings().data_dir) / "s3-cache"
        self._cache_root.mkdir(parents=True, exist_ok=True)
        self._session = aioboto3.Session(**self._session_kwargs)

    def _client(self):  # type: ignore[no-untyped-def]
        return self._session.client("s3", endpoint_url=self._endpoint)

    async def put(self, key: str, file: UploadFile) -> str:
        async with self._client() as s3:
            await s3.upload_fileobj(file.file, self.bucket, key)
        return key

    async def get_path(self, key: str) -> Path:
        """Stage the object on disk for tools (Docling, OCR) that want a path."""
        cache_path = self._cache_root / key
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        if cache_path.exists():
            return cache_path
        async with self._client() as s3:
            await s3.download_file(self.bucket, key, str(cache_path))
        return cache_path

    async def delete_prefix(self, prefix: str) -> None:
        async with self._client() as s3:
            paginator = s3.get_paginator("list_objects_v2")
            async for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
                contents = page.get("Contents") or []
                if not contents:
                    continue
                await s3.delete_objects(
                    Bucket=self.bucket,
                    Delete={"Objects": [{"Key": o["Key"]} for o in contents]},
                )
