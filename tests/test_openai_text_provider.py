from studio.models.render import WorldAppearancePlan
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


    relation_ref = element_schema["properties"]["relations"]["items"]["$ref"]
    relation_name = relation_ref.rsplit("/", 1)[-1]
    relation_schema = schema["$defs"][relation_name]
    assert set(relation_schema["required"]) == set(relation_schema["properties"])
    assert relation_schema["additionalProperties"] is False

    def contains_default(value):
        if isinstance(value, dict):
            return "default" in value or any(
                contains_default(item) for item in value.values()
            )
        if isinstance(value, list):
            return any(contains_default(item) for item in value)
        return False

    assert not contains_default(schema)


def test_text_strict_schema_supports_nested_appearance_contract():
    schema = OpenAIStructuredTextProvider._strict_schema(
        WorldAppearancePlan.model_json_schema()
    )
    object_ref = schema["properties"]["objects"]["items"]["$ref"]
    object_name = object_ref.rsplit("/", 1)[-1]
    object_schema = schema["$defs"][object_name]
    assert set(object_schema["required"]) == set(object_schema["properties"])
    part_ref = object_schema["properties"]["parts"]["items"]["$ref"]
    part_name = part_ref.rsplit("/", 1)[-1]
    part_schema = schema["$defs"][part_name]
    assert set(part_schema["required"]) == set(part_schema["properties"])
