from __future__ import annotations

import base64

import requests

from studio.providers.base import ImageGenerationProvider


OPENAI_IMAGE_ENDPOINT = "https://api.openai.com/v1/images/generations"


class ImageGenerationError(RuntimeError):
    pass


class OpenAIImageProvider(ImageGenerationProvider):
    """OpenAI GPT Image adapter.

    Mini Utopia style rules are deliberately composed elsewhere. This adapter
    only translates a provider-neutral prompt into an Image API request.
    """

    def __init__(
        self,
        api_key: str,
        *,
        model: str = "gpt-image-2",
        timeout_seconds: int = 180,
    ):
        if not api_key:
            raise ValueError("OpenAI API key is required.")
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds

    def generate(
        self,
        *,
        prompt: str,
        size: str = "1024x1536",
        quality: str = "medium",
    ) -> bytes:
        response = requests.post(
            OPENAI_IMAGE_ENDPOINT,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "prompt": prompt,
                "size": size,
                "quality": quality,
            },
            timeout=self.timeout_seconds,
        )

        if response.status_code >= 400:
            try:
                payload = response.json()
                message = payload.get("error", {}).get("message") or response.text
            except ValueError:
                message = response.text
            raise ImageGenerationError(
                f"OpenAI image generation failed ({response.status_code}): {message}"
            )

        payload = response.json()
        data = payload.get("data") or []
        if not data or not data[0].get("b64_json"):
            raise ImageGenerationError("OpenAI image generation returned no image data.")

        try:
            return base64.b64decode(data[0]["b64_json"])
        except (ValueError, TypeError) as exc:
            raise ImageGenerationError("OpenAI image generation returned invalid image data.") from exc
