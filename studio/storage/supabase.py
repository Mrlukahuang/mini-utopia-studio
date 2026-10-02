from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

import requests

from studio.storage.base import ObjectStorage


class SupabaseObjectStorage(ObjectStorage):
    """Private-bucket Supabase Storage backend.

    Credentials stay server-side. Paths returned by this class are logical
    object keys and remain compatible with the existing ObjectStorage contract.
    """

    def __init__(
        self,
        *,
        url: str,
        service_role_key: str,
        bucket: str,
        timeout_seconds: float = 30.0,
    ):
        if not url:
            raise ValueError("Supabase URL is required.")
        if not service_role_key:
            raise ValueError("Supabase service-role key is required.")
        if not bucket:
            raise ValueError("Supabase storage bucket is required.")

        self.url = url.rstrip("/")
        self.service_role_key = service_role_key
        self.bucket = bucket.strip("/")
        self.timeout_seconds = timeout_seconds

    def _headers(self, *, content_type: str | None = None) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.service_role_key}",
            "apikey": self.service_role_key,
        }
        if content_type:
            headers["Content-Type"] = content_type
        return headers

    def _object_url(self, relative_path: str, *, authenticated: bool = False) -> str:
        cleaned = relative_path.strip("/")
        encoded_bucket = quote(self.bucket, safe="")
        encoded_path = quote(cleaned, safe="/")
        access = "authenticated/" if authenticated else ""
        return (
            f"{self.url}/storage/v1/object/"
            f"{access}{encoded_bucket}/{encoded_path}"
        )

    def put_bytes(self, relative_path: str, payload: bytes) -> str:
        cleaned = relative_path.strip("/")
        if not cleaned:
            raise ValueError("Storage path cannot be empty.")

        response = requests.post(
            self._object_url(cleaned),
            headers={
                **self._headers(content_type="application/octet-stream"),
                "x-upsert": "true",
            },
            data=payload,
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        return cleaned

    def exists(self, relative_path: str) -> bool:
        response = requests.get(
            self._object_url(relative_path, authenticated=True),
            headers=self._headers(),
            timeout=self.timeout_seconds,
        )
        if response.status_code == 404:
            return False
        response.raise_for_status()
        return True

    def get_bytes(self, relative_path: str) -> bytes:
        response = requests.get(
            self._object_url(relative_path, authenticated=True),
            headers=self._headers(),
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        return response.content

    def resolve(self, relative_path: str) -> Path:
        raise RuntimeError(
            "SupabaseObjectStorage has no local filesystem path. "
            "Use get_bytes()/put_bytes() instead."
        )

    @property
    def backend_name(self) -> str:
        return "supabase"
