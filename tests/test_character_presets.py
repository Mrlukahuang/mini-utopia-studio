from studio.models.character import CharacterProfile
from studio.ui.creator.character_presets import (
    CUSTOM,
    CHARACTER_TYPE_OPTIONS,
    COLOR_PRESETS,
    PERSONALITY_OPTIONS,
)


def test_custom_build_presets_end_with_custom_escape_hatch():
    assert CHARACTER_TYPE_OPTIONS[-1] == CUSTOM
    assert PERSONALITY_OPTIONS[-1] == CUSTOM
    assert CUSTOM in COLOR_PRESETS


def test_character_profile_v13_stores_single_creator_extra_details_field():
    profile = CharacterProfile(
        creator_extra_details="来自云朵花园，看到 Portal 会发光。"
    )

    assert profile.schema_version == "1.3"
    assert "云朵花园" in profile.creator_extra_details
