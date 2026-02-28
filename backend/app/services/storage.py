"""
Storage Service
---------------
Handles file uploads to Supabase Storage.
Returns the storage path which is saved alongside document metadata in PostgreSQL.
"""

import asyncio
import uuid
import functools

from supabase import create_client, Client
from app.config.settings import settings


class StorageService:
    def __init__(self):
        self._client: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
        self._bucket = settings.SUPABASE_STORAGE_BUCKET
        self._bucket_ready = False

    def _ensure_bucket(self) -> None:
        """Creates the bucket if it does not already exist (idempotent)."""
        try:
            buckets = [b.name for b in self._client.storage.list_buckets()]
        except Exception:
            buckets = []
        if self._bucket not in buckets:
            self._client.storage.create_bucket(self._bucket, options={"public": False})
        self._bucket_ready = True

    def _sync_upload(self, unique_name: str, content: bytes, content_type: str) -> str:
        if not self._bucket_ready:
            self._ensure_bucket()
        self._client.storage.from_(self._bucket).upload(
            path=unique_name,
            file=content,
            file_options={"content-type": content_type},
        )
        return unique_name

    def _sync_get_url(self, storage_path: str) -> str:
        response = self._client.storage.from_(self._bucket).create_signed_url(
            storage_path, expires_in=3600
        )
        return response["signedURL"]

    async def upload(self, filename: str, content: bytes, content_type: str = "application/octet-stream") -> str:
        """Uploads a file to Supabase Storage (non-blocking)."""
        unique_name = f"{uuid.uuid4()}_{filename}"
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            functools.partial(self._sync_upload, unique_name, content, content_type),
        )

    async def get_url(self, storage_path: str) -> str:
        """Returns a signed URL for downloading a stored file (non-blocking)."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            functools.partial(self._sync_get_url, storage_path),
        )
