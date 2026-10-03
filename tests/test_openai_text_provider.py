from studio.models.world import WorldPromptInterpretation
from studio.providers.openai_text import OpenAIStructuredTextProvider


def test_strict_schema_requires_nested_fields_and_removes_defaults():
    schema = OpenAIStructuredTextProvider._strict_schema(
        WorldPromptInterpretation.model_json_schema()
    )

    assert set(schema["required"]) == set(schema["properties"])
    assert schema["additionalProperties"] is False

    scene_ref = schema["properties"]["scene_plan"]["$ref"]
    scene_name = scene_ref.rsplit("/", 1)[-1]
    scene_schema = schema["$defs"][scene_name]
    assert set(scene_schema["required"]) == set(scene_schema["properties"])
    assert scene_schema["additionalProperties"] is False

    element_ref = scene_schema["properties"]["elements"]["items"]["$ref"]
    element_name = element_ref.rsplit("/", 1)[-1]
    element_schema = schema["$defs"][element_name]
    assert set(element_schema["required"]) == set(element_schema["properties"])
    assert element_schema["additionalProperties"] is False

    def contains_default(value):
        if isinstance(value, dict):
            return "default" in value or any(
                contains_default(item) for item in value.values()
            )
        if isinstance(value, list):
            return any(contains_default(item) for item in value)
        return False

    assert not contains_default(schema)
