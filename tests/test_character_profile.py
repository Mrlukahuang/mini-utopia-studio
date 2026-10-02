import pytest
from pydantic import ValidationError

from studio.core.enums import AssetType
from studio.models.asset import Asset
from studio.models.character import (
    CharacterProfile,
    EyeProfile,
    WearableLoadout,
)


def test_character_profile_v1_core_completion():
    profile = CharacterProfile(
        character_type="机器人",
        age="10",
        appearance="银色的小机器人",
        hair_or_fur_color="银灰色",
        body_build="普通 / Average",
        height="偏矮 / Short",
        eyes=EyeProfile(shape="圆形", color="蓝色"),
        personality_traits=["好奇", "勇敢"],
        speaking_tone="轻快、直接",
        native_language="中文",
        english_level=6,
    )

    assert profile.schema_version == "1.0"
    assert profile.missing_core_fields() == []


def test_character_profile_reports_missing_core_fields():
    profile = CharacterProfile(character_type="大熊猫")

    missing = profile.missing_core_fields()

    assert "character_type" not in missing
    assert "age" in missing
    assert "appearance" in missing
    assert "personality_traits" in missing
    assert "speaking_tone" in missing
    assert "native_language" in missing
    assert "english_level" in missing


def test_english_level_must_be_between_1_and_10():
    with pytest.raises(ValidationError):
        CharacterProfile(english_level=0)

    with pytest.raises(ValidationError):
        CharacterProfile(english_level=11)


def test_starting_props_are_limited_to_two():
    profile = CharacterProfile(starting_prop_ids=["PROP_one", "PROP_two"])
    assert len(profile.starting_prop_ids) == 2

    with pytest.raises(ValidationError):
        CharacterProfile(
            starting_prop_ids=["PROP_one", "PROP_two", "PROP_three"]
        )


def test_wearables_reference_reusable_asset_ids():
    profile = CharacterProfile(
        wearables=WearableLoadout(
            top_id="WEAR_top",
            bottom_id="WEAR_bottom",
            shoes_id="WEAR_shoes",
            hat_id="WEAR_hat",
            accessory_ids=["WEAR_bag"],
        )
    )

    assert profile.wearables.top_id == "WEAR_top"
    assert profile.wearables.accessory_ids == ["WEAR_bag"]


def test_wearable_asset_uses_wear_prefix():
    asset = Asset.create(
        AssetType.WEARABLE,
        display_name="黄色雨帽",
        slug="yellow-rain-hat",
    )

    assert asset.asset_id.startswith("WEAR_")


def test_visual_difference_fields_are_preserved():
    profile = CharacterProfile(
        hair_or_fur="头发",
        hair_style="双辫 / Twin braids",
        hair_or_fur_color="紫色",
        body_build="圆润 / Round",
        height="很高 / Very tall",
    )

    assert profile.hair_style == "双辫 / Twin braids"
    assert profile.hair_or_fur_color == "紫色"
    assert profile.body_build == "圆润 / Round"
    assert profile.height == "很高 / Very tall"
