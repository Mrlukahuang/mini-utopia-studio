import base64

import pytest

from studio.providers.openai_image import (
    ImageGenerationError,
    OpenAIImageProvider,
)


class FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)

    def json(self):
        return self._payload


def test_openai_image_provider_decodes_base64(monkeypatch):
    captured = {}
    raw = b"png-data"

    def fake_post(url, *, headers, json, timeout):
        captured.update({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return FakeResponse(
            200,
            {"data": [{"b64_json": base64.b64encode(raw).decode("ascii")}]},
        )

    monkeypatch.setattr("studio.providers.openai_image.requests.post", fake_post)

    provider = OpenAIImageProvider("secret", model="gpt-image-2")
    result = provider.generate(prompt="hello", size="1024x1536", quality="medium")

    assert result == raw
    assert captured["json"]["model"] == "gpt-image-2"
    assert captured["json"]["size"] == "1024x1536"
    assert captured["headers"]["Authorization"] == "Bearer secret"


def test_openai_image_provider_raises_clean_error(monkeypatch):
    def fake_post(url, *, headers, json, timeout):
        return FakeResponse(400, {"error": {"message": "bad request"}})

    monkeypatch.setattr("studio.providers.openai_image.requests.post", fake_post)

    provider = OpenAIImageProvider("secret")

    with pytest.raises(ImageGenerationError, match="bad request"):
        provider.generate(prompt="hello")
