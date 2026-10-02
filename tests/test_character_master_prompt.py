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
    assert "2.75 to 3.25 heads tall" in prompt
    assert "large readable eyes" in prompt
    assert "canonical identity reference" in prompt
    assert "Do not imitate branded characters" in prompt
