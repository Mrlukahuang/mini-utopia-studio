from pathlib import Path

from studio.core.config import Settings
from studio.services.bootstrap import build_context
from studio.services.style_service import StyleService
from studio.services.character_master_prompt_service import CharacterMasterPromptService
from studio.services.reusable_asset_library_service import ReusableAssetLibraryService
from studio.services.reusable_asset_pack_service import ReusableAssetPackService
from studio.services.world_hero_composition_service import WorldHeroCompositionService
from studio.providers.hero_asset import HuggingFacePixal3DProvider, HttpHeroAssetProvider


def test_build_context_exposes_style_service(tmp_path):
    settings = Settings(
        root_dir=tmp_path,
        data_dir=tmp_path / "data",
        database_path=tmp_path / "data" / "studio.db",
        app_env="test",
        openai_api_key=None,
        gemini_api_key=None,
    )
    settings.data_dir.mkdir(parents=True, exist_ok=True)

    ctx = build_context(settings)

    assert isinstance(ctx.styles, StyleService)


def test_build_context_exposes_character_master_prompt_service(tmp_path):
    settings = Settings(
        root_dir=tmp_path,
        data_dir=tmp_path / "data",
        database_path=tmp_path / "data" / "studio.db",
        app_env="test",
        openai_api_key=None,
        gemini_api_key=None,
    )
    settings.data_dir.mkdir(parents=True, exist_ok=True)

    ctx = build_context(settings)

    assert isinstance(ctx.character_master_prompts, CharacterMasterPromptService)


def test_build_context_exposes_reusable_asset_library(tmp_path):
    settings = Settings(
        root_dir=tmp_path,
        data_dir=tmp_path / "data",
        database_path=tmp_path / "data" / "studio.db",
        app_env="test",
        openai_api_key=None,
        gemini_api_key=None,
    )
    settings.data_dir.mkdir(parents=True, exist_ok=True)

    ctx = build_context(settings)

    assert isinstance(ctx.reusable_assets, ReusableAssetLibraryService)



def test_build_context_exposes_reusable_asset_pack_service(tmp_path):
    settings = Settings(
        root_dir=tmp_path,
        data_dir=tmp_path / "data",
        database_path=tmp_path / "data" / "studio.db",
        app_env="test",
        openai_api_key=None,
        gemini_api_key=None,
    )
    settings.data_dir.mkdir(parents=True, exist_ok=True)

    ctx = build_context(settings)

    assert isinstance(ctx.reusable_asset_packs, ReusableAssetPackService)
    assert ctx.reusable_asset_packs.library is ctx.reusable_assets



def test_build_context_exposes_hero_composition_resolver(tmp_path):
    settings = Settings(
        root_dir=tmp_path,
        data_dir=tmp_path / "data",
        database_path=tmp_path / "data" / "studio.db",
        app_env="test",
        openai_api_key=None,
        gemini_api_key=None,
    )
    settings.data_dir.mkdir(parents=True, exist_ok=True)

    ctx = build_context(settings)

    assert isinstance(ctx.world_hero_compositions, WorldHeroCompositionService)
    assert ctx.world_concepts.hero_composition_service is ctx.world_hero_compositions


def test_build_context_uses_hf_pixal3d_when_token_is_configured(tmp_path):
    settings = Settings(
        root_dir=tmp_path,
        data_dir=tmp_path / "data",
        database_path=tmp_path / "data" / "studio.db",
        app_env="test",
        openai_api_key=None,
        gemini_api_key=None,
        hf_token="hf-test-token",
        hf_hero_space_id="TencentARC/Pixal3D",
        hf_pixal3d_resolution=1024,
    )
    settings.data_dir.mkdir(parents=True, exist_ok=True)

    ctx = build_context(settings)

    assert isinstance(ctx.world_hero_assets.provider, HuggingFacePixal3DProvider)
    assert ctx.world_hero_assets.reusable_library is ctx.reusable_assets
    assert ctx.world_hero_assets.provider.space_id == "TencentARC/Pixal3D"


def test_build_context_worker_override_takes_precedence_over_hf(tmp_path):
    settings = Settings(
        root_dir=tmp_path,
        data_dir=tmp_path / "data",
        database_path=tmp_path / "data" / "studio.db",
        app_env="test",
        openai_api_key=None,
        gemini_api_key=None,
        hero_asset_worker_url="https://worker.example.test",
        hf_token="hf-test-token",
    )
    settings.data_dir.mkdir(parents=True, exist_ok=True)

    ctx = build_context(settings)

    assert isinstance(ctx.world_hero_assets.provider, HttpHeroAssetProvider)
