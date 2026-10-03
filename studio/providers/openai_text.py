from __future__ import annotations

import json
from typing import Type

import requests
from pydantic import BaseModel

from studio.providers.base import StructuredTextProvider


OPENAI_RESPONSES_ENDPOINT = "https://api.openai.com/v1/responses"


class OpenAIStructuredTextError(RuntimeError):
    pass


class OpenAIStructuredTextProvider(StructuredTextProvider):
    """OpenAI Responses API adapter for validated structured text planning."""

    def __init__(
        self,
        api_key: str,
        *,
        model: str,
        timeout_seconds: int = 120,
    ):
        if not api_key:
            raise ValueError("OpenAI API key is required.")
        if not model:
            raise ValueError("OpenAI text model is required.")
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds

    def generate_structured(
        self,
        *,
        system: str,
        user: str,
        schema: Type[BaseModel],
    ) -> BaseModel:
        schema_json = self._strict_schema(schema.model_json_schema())
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
                        "role": "system",
                        "content": [{"type": "input_text", "text": system}],
                    },
                    {
                        "role": "user",
                        "content": [{"type": "input_text", "text": user}],
                    },
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
            raise OpenAIStructuredTextError(
                f"OpenAI structured text failed ({response.status_code}): {message}"
            )

        payload = response.json()
        text = self._extract_output_text(payload)
        if not text:
            raise OpenAIStructuredTextError(
                "OpenAI structured text returned no structured output."
            )
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise OpenAIStructuredTextError(
                "OpenAI structured text returned invalid JSON."
            ) from exc
        return schema.model_validate(parsed)

    @classmethod
    def _strict_schema(cls, value):
        """Make Pydantic JSON Schema compatible with strict structured output."""
        if isinstance(value, dict):
            result = {
                key: cls._strict_schema(item)
                for key, item in value.items()
            }
            properties = result.get("properties")
            if isinstance(properties, dict):
                result["required"] = list(properties)
                result["additionalProperties"] = False
            return result
        if isinstance(value, list):
            return [cls._strict_schema(item) for item in value]
        return value

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
