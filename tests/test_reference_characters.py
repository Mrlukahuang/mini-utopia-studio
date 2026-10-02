import pytest
from pydantic import ValidationError

from studio.models.reference import ReferenceCharacterConfig


def test_reference_character_scale_uses_two_character_ids():
    config = ReferenceCharacterConfig(
        character_asset_ids=["CHAR_chelsea", "CHAR_charlotte"],
    )

    assert config.character_asset_ids == ["CHAR_chelsea", "CHAR_charlotte"]


def test_reference_character_scale_requires_distinct_characters():
    with pytest.raises(ValidationError):
        ReferenceCharacterConfig(
            character_asset_ids=["CHAR_same", "CHAR_same"],
        )


def test_reference_height_bounds_use_half_and_double_by_default():
    config = ReferenceCharacterConfig(
        character_asset_ids=["CHAR_shorter", "CHAR_taller"],
    )

    minimum, maximum = config.height_bounds([110, 140])

    assert minimum == 55
    assert maximum == 280
