from studio.core.enums import AssetType, ReviewStatus
from studio.repositories.sqlite import SQLiteStudioRepository
from studio.services.style_service import StyleService
from studio.services.universe_service import UniverseService


def test_mini_utopia_base_style_is_idempotent(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    service = StyleService(repo)

    first = service.ensure_mini_utopia_base()
    second = service.ensure_mini_utopia_base()

    assert first.asset_id == second.asset_id
    assert first.asset_type == AssetType.STYLE
    assert first.status == ReviewStatus.APPROVED


def test_base_style_contains_five_visual_dna_pillars(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    style = StyleService(repo).ensure_mini_utopia_base()

    profile = style.metadata["style_profile"]

    assert len(profile["visual_dna_pillars"]) == 5
    assert "Miniature / 微缩世界" in profile["visual_dna_pillars"]
    assert "Macaron Dreamscape / 马卡龙梦幻世界" in profile["visual_dna_pillars"]
    assert profile["composition_guide"].startswith("70%")


def test_base_style_enables_full_macaron_family_behavior(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    style = StyleService(repo).ensure_mini_utopia_base()

    palette = style.metadata["style_profile"]["macaron_palette"]

    assert palette["saturation"] == "low-to-medium"
    assert palette["lightness"] == "high"
    assert "lavender" in palette["enabled_families"]
    assert "mint" in palette["enabled_families"]
    assert "neon-heavy color" in palette["avoid"]


def test_world_style_inheritance_field_exists(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    style = StyleService(repo).ensure_mini_utopia_base()

    profile = style.metadata["style_profile"]

    assert "parent_style_asset_id" in profile
    assert "reference_asset_ids" in profile


def test_base_style_attaches_to_mini_utopia_universe(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    universe = UniverseService(repo).ensure_mini_utopia()

    attached = StyleService(repo).attach_base_style(universe)

    assert attached.style_asset_id is not None
    style = repo.get_asset(attached.style_asset_id)
    assert style is not None
    assert style.asset_type == AssetType.STYLE
