from studio.core.enums import AssetType, ReviewStatus
from studio.models.asset import Asset
from studio.models.world import WorldProfile
from studio.providers.base import ImageGenerationProvider
from studio.repositories.sqlite import SQLiteStudioRepository
from studio.services.style_service import StyleService
from studio.services.world_blueprint_service import WorldBlueprintService
from studio.services.world_concept_prompt_service import WorldConceptPromptService
from studio.services.world_concept_service import WorldConceptService
from studio.storage.local import LocalObjectStorage


class FakeImageProvider(ImageGenerationProvider):
    def generate(self, *, prompt: str, size: str = "1536x1024", quality: str = "medium") -> bytes:
        return b"fake-world-png"


def test_approve_world_concept_persists_concept_and_blueprint(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    storage = LocalObjectStorage(tmp_path / "storage")
    service = WorldConceptService(
        repo,
        storage,
        WorldConceptPromptService(),
        WorldBlueprintService(),
        image_provider=FakeImageProvider(),
    )

    profile = WorldProfile(
        world_name="Pastel Star Garden",
        world_type="Floating Islands / 漂浮岛",
        reality_mode="Fantasy / 幻想",
        terrain=["Meadow / 草地"],
        mood=["Dreamy / 梦幻"],
        portal_form="Star Arch / 星星拱门",
        landmark_ideas=["Portal Plaza / 传送门广场"],
        playable=True,
    )
    world = Asset.create(
        AssetType.LOCATION,
        display_name="Pastel Star Garden",
        slug="pastel-star-garden",
        metadata={"world_profile": profile.model_dump(mode="json")},
    )
    repo.save_asset(world)
    style = StyleService(repo).ensure_mini_utopia_base()

    candidate = service.generate_candidate(
        location_asset_id=world.asset_id,
        style_asset_id=style.asset_id,
        direction="playable",
    )
    service.approve_candidate(
        location_asset_id=world.asset_id,
        candidate_path=candidate.path,
        style_asset_id=style.asset_id,
    )

    saved = repo.get_asset(world.asset_id)
    assert saved is not None
    assert saved.status == ReviewStatus.APPROVED
    assert saved.metadata["world_concept_path"] == candidate.path
    assert saved.metadata["world_blueprint"]
    assert any(
        file_ref.role == "world_concept_approved" and file_ref.path == candidate.path
        for file_ref in saved.files
    )


def test_rebuild_blueprint_from_current_concept_upgrades_legacy_world(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    storage = LocalObjectStorage(tmp_path / "storage")
    service = WorldConceptService(
        repo,
        storage,
        WorldConceptPromptService(),
        WorldBlueprintService(),
        image_provider=FakeImageProvider(),
    )

    profile = WorldProfile(
        world_name="Legacy Star Garden",
        world_type="Floating Islands / 漂浮岛",
        reality_mode="Fantasy / 幻想",
        terrain=["Meadow / 草地"],
        mood=["Dreamy / 梦幻"],
        portal_form="Star Arch / 星星拱门",
        landmark_ideas=["Portal Plaza / 传送门广场"],
        playable=True,
    )
    world = Asset.create(
        AssetType.LOCATION,
        display_name="Legacy Star Garden",
        slug="legacy-star-garden",
        metadata={"world_profile": profile.model_dump(mode="json")},
    )
    repo.save_asset(world)
    style = StyleService(repo).ensure_mini_utopia_base()

    candidate = service.generate_candidate(
        location_asset_id=world.asset_id,
        style_asset_id=style.asset_id,
        direction="playable",
    )
    service.approve_candidate(
        location_asset_id=world.asset_id,
        candidate_path=candidate.path,
        style_asset_id=style.asset_id,
    )

    legacy = repo.get_asset(world.asset_id)
    assert legacy is not None
    original_version = legacy.version
    legacy.metadata["world_blueprint"]["layout_elements"] = []
    legacy.metadata["world_concept_match_reviewed"] = True
    legacy.metadata["world_concept_match_reviewed_at"] = "2026-01-01T00:00:00+00:00"
    legacy.metadata["world_concept_match_history"] = [{"action": "left"}]
    repo.save_asset(legacy)

    rebuilt = service.rebuild_blueprint_from_current_concept(
        location_asset_id=world.asset_id,
        style_asset_id=style.asset_id,
    )

    assert rebuilt.layout_elements
    saved = repo.get_asset(world.asset_id)
    assert saved is not None
    assert saved.version == original_version
    assert saved.metadata["world_concept_path"] == candidate.path
    assert saved.metadata["world_blueprint"]["layout_elements"]
    assert saved.metadata["world_concept_match_reviewed"] is False
    assert "world_concept_match_reviewed_at" not in saved.metadata
    assert saved.metadata["world_concept_match_history"] == []
    assert saved.metadata["world_blueprint_legacy_upgraded"] is True
