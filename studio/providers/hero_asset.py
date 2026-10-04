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
