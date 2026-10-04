from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass

import requests

from studio.models.render import ObjectAppearanceSpec


@dataclass(frozen=True)
class HeroAssetResult:
    payload: bytes
    mime_type: str
    model: str
    provider: str
    metadata: dict


class HeroAssetProvider(ABC):
    @abstractmethod
    def generate(
        self,
        *,
        image_bytes: bytes,
        mime_type: str,
        element_id: str,
        appearance: ObjectAppearanceSpec,
    ) -> HeroAssetResult: ...


class HttpHeroAssetProvider(HeroAssetProvider):
    """Thin client for a separately deployed GPU Hero Asset Worker."""

    def __init__(
        self,
        *,
        base_url: str,
        model: str = "pixal3d",
        token: str | None = None,
        timeout_seconds: float = 900.0,
    ):
        cleaned = base_url.rstrip("/")
        if not cleaned:
            raise ValueError("Hero Asset Worker URL is required.")
        if model not in {"pixal3d", "triposr"}:
            raise ValueError(f"Unsupported Hero Asset model: {model}")
        self.base_url = cleaned
        self.model = model
        self.token = token
        self.timeout_seconds = timeout_seconds

    def generate(
        self,
        *,
        image_bytes: bytes,
        mime_type: str,
        element_id: str,
        appearance: ObjectAppearanceSpec,
    ) -> HeroAssetResult:
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        response = requests.post(
            f"{self.base_url}/generate",
            headers=headers,
            files={
                "image": (
                    f"{element_id}.png",
                    image_bytes,
                    mime_type,
                )
            },
            data={
                "model": self.model,
                "element_id": element_id,
                "appearance_json": json.dumps(
                    appearance.model_dump(mode="json"),
                    ensure_ascii=False,
                ),
            },
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        payload = response.content
        if not payload:
            raise RuntimeError("Hero Asset Worker returned an empty GLB payload.")

        content_type = response.headers.get(
            "Content-Type",
            "model/gltf-binary",
        ).split(";", 1)[0].strip()
        if content_type not in {
            "model/gltf-binary",
            "application/octet-stream",
        }:
            raise RuntimeError(
                "Hero Asset Worker returned unexpected content type: "
                f"{content_type}"
            )

        return HeroAssetResult(
            payload=payload,
            mime_type="model/gltf-binary",
            model=self.model,
            provider="http_worker",
            metadata={
                "worker_url": self.base_url,
                "content_length": len(payload),
            },
        )


class HuggingFacePixal3DProvider(HeroAssetProvider):
    """Authenticated client for the public TencentARC/Pixal3D ZeroGPU Space.

    Pixal3D's current Space exposes three named Gradio Server endpoints:
    /preprocess -> /generate_3d -> /extract_glb_api. The HF token is passed to
    gradio_client.Client so ZeroGPU usage is attributed to the authenticated
    Hugging Face account instead of the anonymous quota.
    """

    def __init__(
        self,
        *,
        token: str,
        space_id: str = "TencentARC/Pixal3D",
        resolution: int = 1024,
        decimation_target: int = 300_000,
        texture_size: int = 2048,
        seed: int = 42,
        client_factory=None,
        handle_file_fn=None,
    ):
        if not token.strip():
            raise ValueError("HF_TOKEN is required for Hugging Face Pixal3D.")
        if resolution not in {1024, 1536}:
            raise ValueError("Pixal3D resolution must be 1024 or 1536.")
        if not 100_000 <= decimation_target <= 1_000_000:
            raise ValueError(
                "Pixal3D decimation_target must be between 100000 and 1000000."
            )
        if texture_size not in {1024, 2048, 4096}:
            raise ValueError("Pixal3D texture_size must be 1024, 2048, or 4096.")

        self.token = token
        self.space_id = space_id.strip() or "TencentARC/Pixal3D"
        self.resolution = resolution
        self.decimation_target = decimation_target
        self.texture_size = texture_size
        self.seed = int(seed)
        self.model = "pixal3d"
        self._client_factory = client_factory
        self._handle_file_fn = handle_file_fn

    @property
    def cache_identity(self) -> str:
        return (
            f"hf-space:{self.space_id}:pixal3d:"
            f"r{self.resolution}:d{self.decimation_target}:"
            f"t{self.texture_size}:s{self.seed}"
        )

    @staticmethod
    def _unwrap_single(value):
        while isinstance(value, (tuple, list)) and len(value) == 1:
            value = value[0]
        return value

    @classmethod
    def _file_path(cls, value) -> str:
        value = cls._unwrap_single(value)
        if isinstance(value, str):
            return value
        if hasattr(value, "path"):
            return str(value.path)
        if isinstance(value, dict):
            for key in ("path", "name"):
                candidate = value.get(key)
                if candidate:
                    return str(candidate)
        raise RuntimeError(
            "Pixal3D returned an unsupported file result; "
            f"received {type(value).__name__}."
        )

    def _client_tools(self):
        if self._client_factory is not None and self._handle_file_fn is not None:
            return self._client_factory, self._handle_file_fn
        try:
            from gradio_client import Client, handle_file
        except ImportError as exc:
            raise RuntimeError(
                "Hugging Face Pixal3D requires the gradio_client package."
            ) from exc
        return Client, handle_file

    def generate(
        self,
        *,
        image_bytes: bytes,
        mime_type: str,
        element_id: str,
        appearance: ObjectAppearanceSpec,
    ) -> HeroAssetResult:
        import tempfile
        import uuid
        from pathlib import Path

        if not image_bytes:
            raise ValueError("Pixal3D input image is empty.")

        Client, handle_file = self._client_tools()
        session_id = f"mu-{uuid.uuid4().hex}"
        suffix = ".png" if "png" in mime_type.lower() else ".jpg"

        with tempfile.TemporaryDirectory(prefix="mini-utopia-pixal3d-") as temp_dir:
            temp = Path(temp_dir)
            input_path = temp / f"{element_id}{suffix}"
            input_path.write_bytes(image_bytes)

            client = Client(
                self.space_id,
                token=self.token,
                verbose=False,
                download_files=str(temp / "downloads"),
            )

            preprocessed = client.predict(
                handle_file(str(input_path)),
                api_name="/preprocess",
            )
            preprocessed_path = self._file_path(preprocessed)

            generated = client.predict(
                image=handle_file(preprocessed_path),
                seed=self.seed,
                resolution=self.resolution,
                ss_guidance_strength=7.5,
                ss_guidance_rescale=0.7,
                ss_sampling_steps=12,
                ss_rescale_t=5.0,
                shape_slat_guidance_strength=7.5,
                shape_slat_guidance_rescale=0.5,
                shape_slat_sampling_steps=12,
                shape_slat_rescale_t=3.0,
                tex_slat_guidance_strength=1.0,
                tex_slat_guidance_rescale=0.0,
                tex_slat_sampling_steps=12,
                tex_slat_rescale_t=3.0,
                manual_fov=-1.0,
                fov_unit="deg",
                session_id=session_id,
                api_name="/generate_3d",
            )
            generated = self._unwrap_single(generated)
            if not isinstance(generated, dict) or not generated.get("state_path"):
                raise RuntimeError(
                    "Pixal3D /generate_3d did not return a state_path."
                )

            glb_result = client.predict(
                state_path=str(generated["state_path"]),
                decimation_target=self.decimation_target,
                texture_size=self.texture_size,
                session_id=session_id,
                api_name="/extract_glb_api",
            )
            glb_path = Path(self._file_path(glb_result))
            if not glb_path.exists():
                raise RuntimeError(
                    f"Pixal3D GLB download was not materialized: {glb_path}"
                )
            payload = glb_path.read_bytes()
            if len(payload) < 12 or payload[:4] != b"glTF":
                raise RuntimeError("Pixal3D returned an invalid GLB payload.")

        return HeroAssetResult(
            payload=payload,
            mime_type="model/gltf-binary",
            model=self.model,
            provider="huggingface_space",
            metadata={
                "space_id": self.space_id,
                "space_url": f"https://huggingface.co/spaces/{self.space_id}",
                "resolution": self.resolution,
                "decimation_target": self.decimation_target,
                "texture_size": self.texture_size,
                "seed": self.seed,
                "element_id": element_id,
                "appearance_element_id": appearance.element_id,
            },
        )
