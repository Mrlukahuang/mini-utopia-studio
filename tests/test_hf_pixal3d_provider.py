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
        self.src = src
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
            path = self.download_files / "hero.glb"
            path.write_bytes(_valid_glb())
            return {"path": str(path)}
        raise AssertionError(f"unexpected api_name: {api_name}")


def fake_handle_file(path: str):
    return {"fake_upload_path": path}


def test_hf_pixal3d_provider_calls_authenticated_three_stage_space_api():
    FakeClient.instances.clear()
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
    assert client.src == "TencentARC/Pixal3D"
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
    assert result.payload == _valid_glb()
    assert result.provider == "huggingface_space"
    assert result.model == "pixal3d"
    assert result.metadata["space_id"] == "TencentARC/Pixal3D"


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
