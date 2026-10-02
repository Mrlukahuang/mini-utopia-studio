from studio.models.character import CharacterProfile, EyeProfile
from studio.services.character_master_prompt_service import CharacterMasterPromptService
from studio.services.style_service import StyleService
from studio.repositories.sqlite import SQLiteStudioRepository


def test_character_master_prompt_includes_profile_and_locked_visual_dna(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    style_asset = StyleService(repo).ensure_mini_utopia_base()
    style_profile = style_asset.metadata["style_profile"]

    profile = CharacterProfile(
        character_type="人类 / Human",
        character_type_description="8-year-old curious traveler",
        age="8",
        appearance="soft rounded proportions",
        eyes=EyeProfile(
            shape="round",
            color="caramel brown",
            color_hex="#7A5238",
            size="large",
        ),
        hair_or_fur="soft wavy hair",
        hair_style="长卷发 / Long curly",
        hair_or_fur_color="dark brown",
        hair_or_fur_color_hex="#5B4036",
        body_build="普通 / Average",
        height_cm=128,
        favorite_colors=["strawberry pink", "mint", "lavender"],
        personality_traits=["curious", "cheerful"],
        speaking_tone="gentle",
        native_language="Chinese",
        english_level=6,
        story_role="旅行者 / Traveler",
    )

    prompt = CharacterMasterPromptService().compose(
        name="Nova",
        profile=profile,
        style_profile=style_profile,
    )

    assert "Nova" in prompt
    assert "人类 / Human" in prompt
    assert "2.8 to 3.0 heads tall" in prompt
    assert "large readable eyes" in prompt
    assert "CHARACTER MASTER SHEET V2" in prompt
    assert "Do not imitate branded characters" in prompt


def test_character_master_prompt_forbids_generated_text_and_uses_swatches(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    style_asset = StyleService(repo).ensure_mini_utopia_base()
    profile = CharacterProfile(
        character_type="动物 / Animal",
        age="4",
        appearance="cute pig",
        eyes=EyeProfile(color="yellow", color_hex="#F6BF03"),
        hair_or_fur_color="Tiffany blue",
        hair_or_fur_color_hex="#00FFE4",
        favorite_color_hexes=["#F7B7D2", "#B9E7D0", "#D7C2F3"],
        personality_traits=["好奇"],
        speaking_tone="开朗",
        native_language="中文",
        english_level=4,
    )

    prompt = CharacterMasterPromptService().compose(
        name="Piggy",
        profile=profile,
        style_profile=style_asset.metadata["style_profile"],
        wearable_descriptions={
            "top": "pink hoodie",
            "bottom": "pink checked shorts",
        },
    )

    assert "Do NOT draw or render any words" in prompt
    assert "front, three-quarter, side, back" in prompt
    assert "neutral, happy, curious, excited, surprised" in prompt
    assert "PORTRAIT" in prompt
    assert "TOP HERO ZONE" in prompt
    assert "#00FFE4" in prompt
    assert "#F6BF03" in prompt
    assert "pink hoodie" in prompt
