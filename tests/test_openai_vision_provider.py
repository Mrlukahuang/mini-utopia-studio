import json

import pytest

from studio.models.render import WorldAppearancePlan
from studio.models.world import WorldVisualAnalysis
from studio.providers.openai_vision import ImageAnalysisError, OpenAIVisionProvider


class FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)

    def json(self):
        return self._payload


def test_openai_vision_provider_sends_image_and_parses_structured_output(monkeypatch):
    captured = {}
    output = {
        "concept_summary": "Pastel floating garden",
        "must_preserve": ["star portal", "floating island"],
        "flexible_details": ["small flower clusters"],
        "palette_hexes": ["#F7B7D2", "#B9E7D0"],
        "composition_notes": ["portal centered in midground"],
        "spatial_relations": ["castle behind portal"],
    }

    def fake_post(url, *, headers, json, timeout):
        captured.update({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return FakeResponse(
            200,
            {
                "output": [
                    {
                        "type": "message",
                        "content": [
                            {"type": "output_text", "text": __import__("json").dumps(output)}
                        ],
                    }
                ]
            },
        )

    monkeypatch.setattr("studio.providers.openai_vision.requests.post", fake_post)

    provider = OpenAIVisionProvider("secret", model="gpt-4o-mini")
    result = provider.analyze_structured(
        image_bytes=b"image-bytes",
        mime_type="image/png",
        prompt="analyze",
        schema=WorldVisualAnalysis,
    )

    assert result.must_preserve == ["star portal", "floating island"]
    assert captured["json"]["model"] == "gpt-4o-mini"
    content = captured["json"]["input"][0]["content"]
    assert content[1]["type"] == "input_image"
    assert content[1]["image_url"].startswith("data:image/png;base64,")
    assert captured["json"]["text"]["format"]["type"] == "json_schema"
    assert captured["json"]["text"]["format"]["strict"] is True


def test_openai_vision_provider_raises_clean_error(monkeypatch):
    def fake_post(url, *, headers, json, timeout):
        return FakeResponse(400, {"error": {"message": "vision unavailable"}})

    monkeypatch.setattr("studio.providers.openai_vision.requests.post", fake_post)

    provider = OpenAIVisionProvider("secret")

    with pytest.raises(ImageAnalysisError, match="vision unavailable"):
        provider.analyze_structured(
            image_bytes=b"x",
            mime_type="image/png",
            prompt="analyze",
            schema=WorldVisualAnalysis,
        )


def test_openai_vision_strict_schema_supports_nested_appearance_contract():
    schema = OpenAIVisionProvider._strict_schema(
        WorldAppearancePlan.model_json_schema()
    )

    assert set(schema["required"]) == set(schema["properties"])
    assert schema["additionalProperties"] is False

    object_ref = schema["properties"]["objects"]["items"]["$ref"]
    object_name = object_ref.rsplit("/", 1)[-1]
    object_schema = schema["$defs"][object_name]
    assert set(object_schema["required"]) == set(object_schema["properties"])
    assert object_schema["additionalProperties"] is False

    part_ref = object_schema["properties"]["main_body"]["$ref"]
    part_name = part_ref.rsplit("/", 1)[-1]
    part_schema = schema["$defs"][part_name]
    assert set(part_schema["required"]) == set(part_schema["properties"])
    assert part_schema["additionalProperties"] is False
