from types import SimpleNamespace

import pytest
import requests

from studio.storage.supabase import SupabaseObjectStorage


class FakeResponse:
    def __init__(self, status_code=200, content=b""):
        self.status_code = status_code
        self.content = content

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"status={self.status_code}")


def _storage():
    return SupabaseObjectStorage(
        url="https://example.supabase.co",
        service_role_key="test-service-role",
        bucket="mini-utopia-assets",
    )


def test_put_bytes_uploads_private_object_with_upsert(monkeypatch):
    calls = {}

    def fake_post(url, *, headers, data, timeout):
        calls.update(url=url, headers=headers, data=data, timeout=timeout)
        return FakeResponse(200)

    monkeypatch.setattr(requests, "post", fake_post)
    storage = _storage()

    path = storage.put_bytes("assets/CHAR_TEST/master.png", b"image-bytes")

    assert path == "assets/CHAR_TEST/master.png"
    assert calls["url"].endswith(
        "/storage/v1/object/mini-utopia-assets/assets/CHAR_TEST/master.png"
    )
    assert calls["headers"]["x-upsert"] == "true"
    assert calls["headers"]["Authorization"] == "Bearer test-service-role"
    assert calls["data"] == b"image-bytes"


def test_get_bytes_uses_authenticated_private_bucket_endpoint(monkeypatch):
    calls = {}

    def fake_get(url, *, headers, timeout):
        calls.update(url=url, headers=headers, timeout=timeout)
        return FakeResponse(200, b"stored-bytes")

    monkeypatch.setattr(requests, "get", fake_get)
    storage = _storage()

    payload = storage.get_bytes("assets/LOC_TEST/concept.png")

    assert payload == b"stored-bytes"
    assert "/storage/v1/object/authenticated/mini-utopia-assets/" in calls["url"]
    assert calls["headers"]["apikey"] == "test-service-role"


def test_exists_returns_false_on_404(monkeypatch):
    monkeypatch.setattr(
        requests,
        "get",
        lambda *args, **kwargs: FakeResponse(404),
    )

    assert _storage().exists("assets/missing.png") is False


def test_resolve_is_not_available_for_remote_storage():
    with pytest.raises(RuntimeError, match="no local filesystem path"):
        _storage().resolve("assets/anything.glb")
