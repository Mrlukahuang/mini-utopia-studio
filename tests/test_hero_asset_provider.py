from __future__ import annotations

import json

from studio.models.render import ObjectAppearanceSpec, ShapePartSpec
from studio.providers.hero_asset import HttpHeroAssetProvider


class FakeResponse:
    def __init__(self):
        self.content = b"glTF-http-worker"
        self.headers = {"Content-Type": "model/gltf-binary"}

    def raise_for_status(self):
        return None


def _appearance() -> ObjectAppearanceSpec:
    return ObjectAppearanceSpec(
        element_id="SCENE_HERO",
        name="Sky Creature",
        silhouette_family="organic_creature",
        main_body=ShapePartSpec(
            part_id="body",
            role="main_body",
            primitive="ellipsoid",
        ),
    )


def test_http_hero_provider_posts_image_model_and_structured_appearance(monkeypatch):
    captured = {}

    def fake_post(url, *, headers, files, data, timeout):
        captured.update(
            {
                "url": url,
                "headers": headers,
                "files": files,
                "data": data,
                "timeout": timeout,
            }
        )
        return FakeResponse()

    monkeypatch.setattr("studio.providers.hero_asset.requests.post", fake_post)

    provider = HttpHeroAssetProvider(
        base_url="https://gpu.example.test/",
        model="pixal3d",
        token="secret",
        timeout_seconds=123,
    )
    result = provider.generate(
        image_bytes=b"png-bytes",
        mime_type="image/png",
        element_id="SCENE_HERO",
        appearance=_appearance(),
    )

    assert captured["url"] == "https://gpu.example.test/generate"
    assert captured["headers"]["Authorization"] == "Bearer secret"
    assert captured["files"]["image"][1] == b"png-bytes"
    assert captured["data"]["model"] == "pixal3d"
    assert captured["data"]["element_id"] == "SCENE_HERO"
    parsed = json.loads(captured["data"]["appearance_json"])
    assert parsed["element_id"] == "SCENE_HERO"
    assert parsed["main_body"]["primitive"] == "ellipsoid"
    assert captured["timeout"] == 123
    assert result.payload == b"glTF-http-worker"
    assert result.mime_type == "model/gltf-binary"
    assert result.model == "pixal3d"


def test_http_hero_provider_rejects_unknown_model():
    try:
        HttpHeroAssetProvider(
            base_url="https://gpu.example.test",
            model="unknown",
        )
    except ValueError as exc:
        assert "Unsupported Hero Asset model" in str(exc)
    else:
        raise AssertionError("Expected unsupported Hero Asset model to fail.")
