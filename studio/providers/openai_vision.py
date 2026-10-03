from __future__ import annotations

import base64
import json
from typing import Type

import requests
from pydantic import BaseModel

from studio.providers.base import ImageAnalysisProvider


OPENAI_RESPONSES_ENDPOINT = "https://api.openai.com/v1/responses"


class ImageAnalysisError(RuntimeError):
    pass


class OpenAIVisionProvider(ImageAnalysisProvider):
    """OpenAI Responses API adapter for structured image analysis."""

    def __init__(
        self,
        api_key: str,
        *,
        model: str = "gpt-4o-mini",
        timeout_seconds: int = 120,
    ):
        if not api_key:
            raise ValueError("OpenAI API key is required.")
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds

    def analyze_structured(
        self,
        *,
        image_bytes: bytes,
        mime_type: str,
        prompt: str,
        schema: Type[BaseModel],
    ) -> BaseModel:
        if not image_bytes:
            raise ValueError("image_bytes must not be empty.")

        data_url = (
            f"data:{mime_type or 'image/png'};base64,"
            + base64.b64encode(image_bytes).decode("ascii")
        )
        schema_json = schema.model_json_schema()

        response = requests.post(
            OPENAI_RESPONSES_ENDPOINT,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "input": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": prompt},
                            {
                                "type": "input_image",
                                "image_url": data_url,
                                "detail": "high",
                            },
                        ],
                    }
                ],
                "text": {
                    "format": {
                        "type": "json_schema",
                        "name": schema.__name__,
                        "strict": True,
                        "schema": schema_json,
                    }
                },
            },
            timeout=self.timeout_seconds,
        )

        if response.status_code >= 400:
            try:
                payload = response.json()
                message = payload.get("error", {}).get("message") or response.text
            except ValueError:
                message = response.text
            raise ImageAnalysisError(
                f"OpenAI image analysis failed ({response.status_code}): {message}"
            )

        payload = response.json()
        text = self._extract_output_text(payload)
        if not text:
            raise ImageAnalysisError("OpenAI image analysis returned no structured output.")

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ImageAnalysisError(
                "OpenAI image analysis returned invalid JSON."
            ) from exc

        return schema.model_validate(parsed)

    @staticmethod
    def _extract_output_text(payload: dict) -> str:
        direct = payload.get("output_text")
        if isinstance(direct, str) and direct.strip():
            return direct

        for item in payload.get("output") or []:
            if item.get("type") != "message":
                continue
            for part in item.get("content") or []:
                if part.get("type") == "output_text" and isinstance(part.get("text"), str):
                    return part["text"]
        return ""
