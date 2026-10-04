from pathlib import Path

from studio.core.config import Settings
from studio.services.bootstrap import build_context
from studio.services.style_service import StyleService
from studio.services.character_master_prompt_service import CharacterMasterPromptService
from studio.services.reusable_asset_library_service import ReusableAssetLibraryService
from studio.services.reusable_asset_pack_service import ReusableAssetPackService


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
