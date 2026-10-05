from __future__ import annotations

import struct
from pathlib import Path

import pytest

from studio.models.render import ObjectAppearanceSpec, ShapePartSpec
from studio.providers.hero_asset import HuggingFacePixal3DProvider


def _appearance() -> ObjectAppearanceSpec:
    return ObjectAppearanceSpec(
        element_id="SCENE_HERO",
        name="Sky Whale",
        silhouette_family="organic_creature",
        main_body=ShapePartSpec(
            part_id="body",
            role="main_body",
            primitive="ellipsoid",
        ),
    )


def _valid_glb() -> bytes:
    return b"glTF" + struct.pack("<II", 2, 12)


class FakeClient:
    instances = []

    def __init__(self, src, *, token, verbose, download_files):
        self.space_id = src
        self.src = "https://tencentarc-pixal3d.hf.space/"
        self.token = token
        self.verbose = verbose
        self.download_files = Path(download_files)
        self.download_files.mkdir(parents=True, exist_ok=True)
        self.calls = []
        FakeClient.instances.append(self)

    def predict(self, *args, api_name, **kwargs):
        self.calls.append(
            {
                "args": args,
                "kwargs": kwargs,
                "api_name": api_name,
            }
        )
        if api_name == "/preprocess":
            path = self.download_files / "preprocessed.png"
            path.write_bytes(b"fake-png")
            return str(path)
        if api_name == "/generate_3d":
            return {
                "state_path": "/remote/tmp/state_123.npz",
                "camera_angle_x": 0.3,
                "distance": 3.0,
            }
        if api_name == "/extract_glb_api":
            assert self.download_files is False
            return {"path": "/home/user/app/tmp/result_123.glb"}
        raise AssertionError(f"unexpected api_name: {api_name}")


def fake_handle_file(path: str):
    return {"fake_upload_path": path}


class FakeStaticResponse:
    def __init__(self, content: bytes):
        self.content = content

    def raise_for_status(self):
        return None


def test_hf_pixal3d_provider_calls_authenticated_three_stage_space_api(monkeypatch):
    FakeClient.instances.clear()
    static_fetch = {}

    def fake_get(url, *, headers, timeout):
        static_fetch.update(
            {"url": url, "headers": headers, "timeout": timeout}
        )
        return FakeStaticResponse(_valid_glb())

    monkeypatch.setattr("studio.providers.hero_asset.requests.get", fake_get)
    provider = HuggingFacePixal3DProvider(
        token="hf-test-secret",
        space_id="TencentARC/Pixal3D",
        resolution=1024,
        decimation_target=300000,
        texture_size=2048,
        seed=42,
        client_factory=FakeClient,
        handle_file_fn=fake_handle_file,
    )

    result = provider.generate(
        image_bytes=b"input-png",
        mime_type="image/png",
        element_id="SCENE_HERO",
        appearance=_appearance(),
    )

    client = FakeClient.instances[-1]
    assert client.space_id == "TencentARC/Pixal3D"
    assert client.src == "https://tencentarc-pixal3d.hf.space/"
    assert client.token == "hf-test-secret"
    assert [call["api_name"] for call in client.calls] == [
        "/preprocess",
        "/generate_3d",
        "/extract_glb_api",
    ]
    generate = client.calls[1]["kwargs"]
    assert generate["seed"] == 42
    assert generate["resolution"] == 1024
    assert generate["session_id"].startswith("mu-")
    extract = client.calls[2]["kwargs"]
    assert extract["state_path"] == "/remote/tmp/state_123.npz"
    assert extract["decimation_target"] == 300000
    assert extract["texture_size"] == 2048
    assert client.download_files is False
    assert static_fetch["url"] == (
        "https://tencentarc-pixal3d.hf.space/tmp/result_123.glb"
    )
    assert static_fetch["headers"]["Authorization"] == "Bearer hf-test-secret"
    assert static_fetch["headers"]["X-HF-Authorization"] == "Bearer hf-test-secret"
    assert static_fetch["timeout"] == 120
    assert result.payload == _valid_glb()
    assert result.provider == "huggingface_space"
    assert result.model == "pixal3d"
    assert result.metadata["space_id"] == "TencentARC/Pixal3D"


def test_hf_pixal3d_provider_records_zero_gpu_quota_delta(monkeypatch):
    FakeClient.instances.clear()

    def fake_get(url, *, headers, timeout):
        return FakeStaticResponse(_valid_glb())

    snapshots = iter(
        [
            {
                "base": 2400,
                "remaining": 2100,
                "overquota_used": 0,
                "resets_at": "2026-10-05T10:00:00+00:00",
            },
            {
                "base": 2400,
                "remaining": 1920,
                "overquota_used": 0,
                "resets_at": "2026-10-05T10:00:00+00:00",
            },
        ]
    )
    monkeypatch.setattr("studio.providers.hero_asset.requests.get", fake_get)
    provider = HuggingFacePixal3DProvider(
        token="hf-test-secret",
        client_factory=FakeClient,
        handle_file_fn=fake_handle_file,
        quota_fetcher=lambda: next(snapshots),
    )

    result = provider.generate(
        image_bytes=b"input-png",
        mime_type="image/png",
        element_id="SCENE_HERO",
        appearance=_appearance(),
    )

    usage = result.metadata["zero_gpu_usage"]
    assert usage["status"] == "ok"
    assert usage["gpu_seconds"] == 180
    assert usage["included_gpu_seconds"] == 180
    assert usage["overquota_gpu_seconds"] == 0
    assert usage["remaining_seconds"] == 1920
    assert usage["base_seconds"] == 2400
    assert usage["wall_seconds"] >= 0


def test_hf_pixal3d_quota_telemetry_failure_never_blocks_generation(monkeypatch):
    FakeClient.instances.clear()

    def fake_get(url, *, headers, timeout):
        return FakeStaticResponse(_valid_glb())

    monkeypatch.setattr("studio.providers.hero_asset.requests.get", fake_get)
    provider = HuggingFacePixal3DProvider(
        token="hf-test-secret",
        client_factory=FakeClient,
        handle_file_fn=fake_handle_file,
        quota_fetcher=lambda: (_ for _ in ()).throw(RuntimeError("billing denied")),
    )

    result = provider.generate(
        image_bytes=b"input-png",
        mime_type="image/png",
        element_id="SCENE_HERO",
        appearance=_appearance(),
    )

    assert result.payload == _valid_glb()
    usage = result.metadata["zero_gpu_usage"]
    assert usage["status"] == "unavailable"
    assert usage["before"]["status"] == "unavailable"
    assert usage["after"]["status"] == "unavailable"


def test_hf_pixal3d_cache_identity_changes_with_quality_profile():
    low = HuggingFacePixal3DProvider(
        token="hf-test",
        resolution=1024,
        decimation_target=300000,
        texture_size=2048,
    )
    high = HuggingFacePixal3DProvider(
        token="hf-test",
        resolution=1536,
        decimation_target=1000000,
        texture_size=4096,
    )

    assert low.cache_identity != high.cache_identity
    assert "r1024" in low.cache_identity
    assert "r1536" in high.cache_identity


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"resolution": 512}, "1024 or 1536"),
        ({"decimation_target": 99999}, "between 100000 and 1000000"),
        ({"texture_size": 512}, "1024, 2048, or 4096"),
    ],
)
def test_hf_pixal3d_provider_validates_quality_profile(kwargs, message):
    with pytest.raises(ValueError, match=message):
        HuggingFacePixal3DProvider(token="hf-test", **kwargs)


def test_hf_pixal3d_provider_requires_token():
    with pytest.raises(ValueError, match="HF_TOKEN"):
        HuggingFacePixal3DProvider(token="")


class FailHighResolutionClient(FakeClient):
    def predict(self, *args, api_name, **kwargs):
        if api_name == "/generate_3d" and kwargs.get("resolution") == 1536:
            self.calls.append(
                {"args": args, "kwargs": kwargs, "api_name": api_name}
            )
            raise RuntimeError("CUDA out of memory")
        return super().predict(*args, api_name=api_name, **kwargs)


class FailHighExtractionClient(FakeClient):
    def predict(self, *args, api_name, **kwargs):
        if (
            api_name == "/extract_glb_api"
            and kwargs.get("texture_size") == 4096
        ):
            self.calls.append(
                {"args": args, "kwargs": kwargs, "api_name": api_name}
            )
            raise RuntimeError("GPU extraction failed")
        return super().predict(*args, api_name=api_name, **kwargs)


def test_hf_pixal3d_high_resolution_falls_back_to_1024(monkeypatch):
    FakeClient.instances.clear()

    def fake_get(url, *, headers, timeout):
        return FakeStaticResponse(_valid_glb())

    monkeypatch.setattr("studio.providers.hero_asset.requests.get", fake_get)
    provider = HuggingFacePixal3DProvider(
        token="hf-test-secret",
        resolution=1536,
        decimation_target=500000,
        texture_size=4096,
        client_factory=FailHighResolutionClient,
        handle_file_fn=fake_handle_file,
        quota_fetcher=lambda: {
            "base": 2400,
            "remaining": 2000,
            "overquota_used": 0,
            "resets_at": "same",
        },
    )

    result = provider.generate(
        image_bytes=b"input-png",
        mime_type="image/png",
        element_id="SCENE_HERO",
        appearance=_appearance(),
    )

    client = FakeClient.instances[-1]
    resolutions = [
        call["kwargs"].get("resolution")
        for call in client.calls
        if call["api_name"] == "/generate_3d"
    ]
    assert resolutions == [1536, 1024]
    assert result.metadata["requested_resolution"] == 1536
    assert result.metadata["resolution"] == 1024
    assert result.metadata["quality_fallbacks"][0]["stage"] == "generate_3d"


def test_hf_pixal3d_high_quality_extract_falls_back_without_regeneration(monkeypatch):
    FakeClient.instances.clear()

    def fake_get(url, *, headers, timeout):
        return FakeStaticResponse(_valid_glb())

    monkeypatch.setattr("studio.providers.hero_asset.requests.get", fake_get)
    provider = HuggingFacePixal3DProvider(
        token="hf-test-secret",
        resolution=1024,
        decimation_target=500000,
        texture_size=4096,
        client_factory=FailHighExtractionClient,
        handle_file_fn=fake_handle_file,
        quota_fetcher=lambda: {
            "base": 2400,
            "remaining": 2000,
            "overquota_used": 0,
            "resets_at": "same",
        },
    )

    result = provider.generate(
        image_bytes=b"input-png",
        mime_type="image/png",
        element_id="SCENE_HERO",
        appearance=_appearance(),
    )

    client = FakeClient.instances[-1]
    generate_calls = [
        call for call in client.calls if call["api_name"] == "/generate_3d"
    ]
    extract_calls = [
        call for call in client.calls if call["api_name"] == "/extract_glb_api"
    ]
    assert len(generate_calls) == 1
    assert extract_calls[0]["kwargs"]["texture_size"] == 4096
    assert extract_calls[1]["kwargs"]["texture_size"] == 2048
    assert extract_calls[1]["kwargs"]["decimation_target"] == 300000
    assert result.metadata["texture_size"] == 2048
    assert result.metadata["decimation_target"] == 300000
    assert result.metadata["quality_fallbacks"][0]["stage"] == "extract_glb"


class FailExtractionFor1536LatentClient(FakeClient):
    def __init__(self, src, *, token, verbose, download_files):
        super().__init__(
            src,
            token=token,
            verbose=verbose,
            download_files=download_files,
        )
        self.last_resolution = None

    def predict(self, *args, api_name, **kwargs):
        if api_name == "/generate_3d":
            self.last_resolution = kwargs.get("resolution")
        if api_name == "/extract_glb_api" and self.last_resolution == 1536:
            self.calls.append(
                {"args": args, "kwargs": kwargs, "api_name": api_name}
            )
            raise RuntimeError("decode/remesh failed for 1536 latent")
        return super().predict(*args, api_name=api_name, **kwargs)


def test_hf_pixal3d_extract_failure_on_1536_regenerates_same_reference_at_1024(
    monkeypatch,
):
    FakeClient.instances.clear()

    def fake_get(url, *, headers, timeout):
        return FakeStaticResponse(_valid_glb())

    monkeypatch.setattr("studio.providers.hero_asset.requests.get", fake_get)
    provider = HuggingFacePixal3DProvider(
        token="hf-test-secret",
        resolution=1536,
        decimation_target=500000,
        texture_size=4096,
        client_factory=FailExtractionFor1536LatentClient,
        handle_file_fn=fake_handle_file,
        quota_fetcher=lambda: {
            "base": 2400,
            "remaining": 2000,
            "overquota_used": 0,
            "resets_at": "same",
        },
    )

    result = provider.generate(
        image_bytes=b"same-reference-png",
        mime_type="image/png",
        element_id="SCENE_HERO",
        appearance=_appearance(),
    )

    client = FakeClient.instances[-1]
    generate_resolutions = [
        call["kwargs"].get("resolution")
        for call in client.calls
        if call["api_name"] == "/generate_3d"
    ]
    extract_profiles = [
        (
            call["kwargs"].get("decimation_target"),
            call["kwargs"].get("texture_size"),
        )
        for call in client.calls
        if call["api_name"] == "/extract_glb_api"
    ]

    assert generate_resolutions == [1536, 1024]
    assert extract_profiles == [
        (500000, 4096),
        (300000, 2048),
        (300000, 2048),
    ]
    assert result.payload == _valid_glb()
    assert result.metadata["requested_resolution"] == 1536
    assert result.metadata["resolution"] == 1024
    assert [
        item["stage"] for item in result.metadata["quality_fallbacks"]
    ] == ["extract_glb", "extract_glb_regenerate"]
