import pytest

from studio.core.enums import AssetType, ReviewStatus
from studio.models.world import WorldProfile
from studio.providers.base import ImageGenerationProvider
from studio.repositories.sqlite import SQLiteStudioRepository
from studio.services.asset_service import AssetService
from studio.services.style_service import StyleService
from studio.services.world_concept_prompt_service import WorldConceptPromptService
from studio.services.world_concept_service import WorldConceptService
from studio.services.world_blueprint_service import WorldBlueprintService
from studio.services.world_scene_plan_service import WorldScenePlanService
from studio.storage.local import LocalObjectStorage


class FakeWorldImageProvider(ImageGenerationProvider):
    def __init__(self):
        self.calls = []

    def generate(self, *, prompt: str, size: str = "1536x1024", quality: str = "medium") -> bytes:
        self.calls.append({"prompt": prompt, "size": size, "quality": quality})
        return b"fake-world-image"


def _profile() -> WorldProfile:
    return WorldProfile(
        world_name="Candy Cloud Valley",
        source_description="A cloud village with sleeping houses that grow stars.",
        world_type="Cloud Village / 云端小镇",
        reality_mode="Fantasy / 幻想",
        terrain=["Floating Land / 漂浮陆地"],
        season="Spring / 春",
        weather="Soft Clouds / 轻云",
        time_of_day="Night / 夜晚",
        mood=["Dreamy / 梦幻"],
        landmark_ideas=["Star Tower / 星星塔"],
        portal_form="Star Arch / 星星拱门",
        theme_color_hexes=["#F7B7D2", "#B9E7D0"],
    )


def test_world_asset_uses_location_identity(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    service = AssetService(repo)

    world = service.create_world(
        name="Candy Cloud Valley",
        description="dream world",
        profile=_profile(),
    )

    assert world.asset_type == AssetType.LOCATION
    assert world.asset_id.startswith("LOC_")
    assert world.metadata["world_profile"]["world_name"] == "Candy Cloud Valley"


def test_world_prompt_inherits_global_style_canon(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    style = StyleService(repo).ensure_mini_utopia_base()
    prompt = WorldConceptPromptService().compose(
        profile=_profile(),
        style_profile=style.metadata["style_profile"],
        direction="dream",
    )

    assert "MINI UTOPIA WORLD CONCEPT ART" in prompt
    assert "Candy Cloud Valley" in prompt
    assert "Worlds use the same original block-built language" in prompt
    assert "high lightness" in prompt
    assert "No text, captions, labels" in prompt


def test_approve_world_concept_initializes_blueprint(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    storage = LocalObjectStorage(tmp_path / "storage")
    assets = AssetService(repo)
    style = StyleService(repo).ensure_mini_utopia_base()
    world = assets.create_world(
        name="Candy Cloud Valley",
        description="dream world",
        profile=_profile(),
    )
    provider = FakeWorldImageProvider()
    service = WorldConceptService(
        repo,
        storage,
        WorldConceptPromptService(),
        WorldBlueprintService(),
        provider,
    )

    candidate = service.generate_candidate(
        location_asset_id=world.asset_id,
        style_asset_id=style.asset_id,
        direction="dream",
    )
    approved = service.approve_candidate(
        location_asset_id=world.asset_id,
        candidate_path=candidate.path,
        style_asset_id=style.asset_id,
    )

    saved = repo.get_asset(world.asset_id)
    assert approved.role == "world_concept_approved"
    assert saved.status == ReviewStatus.APPROVED
    assert saved.metadata["world_concept_path"] == candidate.path
    blueprint = saved.metadata["world_blueprint"]
    assert blueprint["grid"]["width"] == 50
    assert blueprint["grid"]["depth"] == 50
    assert blueprint["style_asset_id"] == style.asset_id
    assert blueprint["location_asset_id"] == world.asset_id
    assert len(blueprint["chunks"]) == 25
    assert blueprint["paths"][0]["path_id"] == "PATH_MAIN"
    assert blueprint["camera_points"]
    assert blueprint["director_tours"]


def test_world_concept_generation_uses_wide_medium_image(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    storage = LocalObjectStorage(tmp_path / "storage")
    assets = AssetService(repo)
    style = StyleService(repo).ensure_mini_utopia_base()
    world = assets.create_world(
        name="Candy Cloud Valley",
        description="dream world",
        profile=_profile(),
    )
    provider = FakeWorldImageProvider()
    service = WorldConceptService(
        repo,
        storage,
        WorldConceptPromptService(),
        WorldBlueprintService(),
        provider,
    )

    service.generate_candidate(
        location_asset_id=world.asset_id,
        style_asset_id=style.asset_id,
        direction="playable",
    )

    assert provider.calls[0]["size"] == "1536x1024"
    assert provider.calls[0]["quality"] == "medium"


def test_blueprint_first_plan_is_playable_before_any_preview(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    storage = LocalObjectStorage(tmp_path / "storage")
    assets = AssetService(repo)
    style = StyleService(repo).ensure_mini_utopia_base()
    profile = _profile().model_copy(
        update={
            "landmark_ideas": ["Portal Plaza / 传送门广场"],
            "portal_form": "Star Arch / 星星拱门",
            "water_features": ["Lake / 湖泊"],
        }
    )
    world = assets.create_world(
        name="Candy Cloud Valley",
        description=profile.source_description,
        profile=profile,
    )
    service = WorldConceptService(
        repo,
        storage,
        WorldConceptPromptService(),
        WorldBlueprintService(),
        image_provider=None,
    )

    scene_plan = WorldScenePlanService().plan_from_profile(profile=profile)
    blueprint = service.plan_blueprint(
        location_asset_id=world.asset_id,
        style_asset_id=style.asset_id,
        scene_plan=scene_plan,
    )

    saved = repo.get_asset(world.asset_id)
    assert saved is not None
    assert saved.status == ReviewStatus.APPROVED
    assert saved.metadata["world_pipeline"] == "blueprint_first_v1"
    assert saved.metadata["world_blueprint_source"] == "scene_plan:custom"
    assert saved.metadata["world_scene_plan"]["source_mode"] == "custom"
    assert "world_concept_path" not in saved.metadata
    assert blueprint.layout_elements
    assert blueprint.portal is not None
    assert len([e for e in blueprint.layout_elements if e.kind == "portal"]) == 1

    plaza = next(e for e in blueprint.layout_elements if "Portal Plaza" in e.name)
    assert plaza.kind == "structure"


def test_blueprint_preview_render_never_mutates_blueprint(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    storage = LocalObjectStorage(tmp_path / "storage")
    assets = AssetService(repo)
    style = StyleService(repo).ensure_mini_utopia_base()
    world = assets.create_world(
        name="Candy Cloud Valley",
        description="dream world",
        profile=_profile(),
    )
    provider = FakeWorldImageProvider()
    service = WorldConceptService(
        repo,
        storage,
        WorldConceptPromptService(),
        WorldBlueprintService(),
        provider,
    )

    scene_plan = WorldScenePlanService().plan_from_profile(profile=_profile())
    service.plan_blueprint(
        location_asset_id=world.asset_id,
        style_asset_id=style.asset_id,
        scene_plan=scene_plan,
    )
    planned = repo.get_asset(world.asset_id)
    assert planned is not None
    before = planned.metadata["world_blueprint"]

    preview = service.render_blueprint_preview(
        location_asset_id=world.asset_id,
        style_asset_id=style.asset_id,
    )

    saved = repo.get_asset(world.asset_id)
    assert saved is not None
    assert saved.metadata["world_blueprint"] == before
    assert saved.metadata["world_pipeline"] == "blueprint_first_v1"
    assert saved.metadata["world_preview_source"] == "blueprint"
    assert saved.metadata["world_preview_path"] == preview.path
    assert "world_concept_path" not in saved.metadata
    assert preview.role == "world_preview"
    assert service.current_preview(world.asset_id).path == preview.path
    assert service.current_concept(world.asset_id) is None
    assert len(provider.calls) == 1
    assert provider.calls[0]["size"] == "1536x1024"
    assert provider.calls[0]["quality"] == "medium"
    assert "BLUEPRINT IS AUTHORITATIVE" in provider.calls[0]["prompt"]
    assert "50x50 PLAYABLE LAYOUT" in provider.calls[0]["prompt"]


def test_blueprint_first_uses_prompt_spatial_relation(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    storage = LocalObjectStorage(tmp_path / "storage")
    assets = AssetService(repo)
    style = StyleService(repo).ensure_mini_utopia_base()
    profile = _profile().model_copy(
        update={
            "source_description": "A Star Arch behind Lake.",
            "portal_form": "Star Arch / 星星拱门",
            "water_features": ["Lake / 湖泊"],
            "landmark_ideas": [],
        }
    )
    world = assets.create_world(
        name="Spatial Garden",
        description=profile.source_description,
        profile=profile,
    )
    service = WorldConceptService(
        repo,
        storage,
        WorldConceptPromptService(),
        WorldBlueprintService(),
        image_provider=None,
    )

    blueprint = service.plan_blueprint(
        location_asset_id=world.asset_id,
        style_asset_id=style.asset_id,
    )

    portal = next(e for e in blueprint.layout_elements if e.kind == "portal")
    lake = next(e for e in blueprint.layout_elements if e.kind == "water")
    assert portal.position.z < lake.position.z


def test_blueprint_preview_rejects_legacy_pipeline(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    storage = LocalObjectStorage(tmp_path / "storage")
    assets = AssetService(repo)
    style = StyleService(repo).ensure_mini_utopia_base()
    world = assets.create_world(
        name="Legacy Garden",
        description="dream world",
        profile=_profile(),
    )
    blueprint = WorldBlueprintService().plan(
        location_asset_id=world.asset_id,
        style_asset_id=style.asset_id,
        profile=_profile(),
    )
    world.metadata["world_blueprint"] = blueprint.model_dump(mode="json")
    repo.save_asset(world)

    provider = FakeWorldImageProvider()
    service = WorldConceptService(
        repo,
        storage,
        WorldConceptPromptService(),
        WorldBlueprintService(),
        provider,
    )

    with pytest.raises(ValueError, match="Blueprint-first plan"):
        service.render_blueprint_preview(
            location_asset_id=world.asset_id,
            style_asset_id=style.asset_id,
        )

    assert provider.calls == []


def test_blueprint_preview_rejects_missing_layout_elements(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    storage = LocalObjectStorage(tmp_path / "storage")
    assets = AssetService(repo)
    style = StyleService(repo).ensure_mini_utopia_base()
    world = assets.create_world(
        name="Broken Blueprint Garden",
        description="dream world",
        profile=_profile(),
    )
    service = WorldConceptService(
        repo,
        storage,
        WorldConceptPromptService(),
        WorldBlueprintService(),
        FakeWorldImageProvider(),
    )
    scene_plan = WorldScenePlanService().plan_from_profile(profile=_profile())
    service.plan_blueprint(
        location_asset_id=world.asset_id,
        style_asset_id=style.asset_id,
        scene_plan=scene_plan,
    )
    saved = repo.get_asset(world.asset_id)
    assert saved is not None
    saved.metadata["world_blueprint"]["layout_elements"] = []
    repo.save_asset(saved)

    with pytest.raises(ValueError, match="layout elements"):
        service.render_blueprint_preview(
            location_asset_id=world.asset_id,
            style_asset_id=style.asset_id,
        )


def test_replanning_archives_old_preview_and_clears_preview_metadata(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    storage = LocalObjectStorage(tmp_path / "storage")
    assets = AssetService(repo)
    style = StyleService(repo).ensure_mini_utopia_base()
    world = assets.create_world(
        name="Preview Garden",
        description="dream world",
        profile=_profile(),
    )
    service = WorldConceptService(
        repo,
        storage,
        WorldConceptPromptService(),
        WorldBlueprintService(),
        FakeWorldImageProvider(),
    )

    scene_plan = WorldScenePlanService().plan_from_profile(profile=_profile())
    service.plan_blueprint(
        location_asset_id=world.asset_id,
        style_asset_id=style.asset_id,
        scene_plan=scene_plan,
    )
    preview = service.render_blueprint_preview(
        location_asset_id=world.asset_id,
        style_asset_id=style.asset_id,
    )
    assert service.current_preview(world.asset_id) is not None

    service.plan_blueprint(
        location_asset_id=world.asset_id,
        style_asset_id=style.asset_id,
        scene_plan=scene_plan,
    )

    saved = repo.get_asset(world.asset_id)
    assert saved is not None
    assert "world_preview_path" not in saved.metadata
    assert "world_preview_source" not in saved.metadata
    assert "world_preview_last_prompt" not in saved.metadata
    assert service.current_preview(world.asset_id) is None
    assert any(
        file_ref.path == preview.path and file_ref.role == "world_preview_archive"
        for file_ref in saved.files
    )


def test_blueprint_preview_rejects_stale_profile_or_scene_plan(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    storage = LocalObjectStorage(tmp_path / "storage")
    assets = AssetService(repo)
    style = StyleService(repo).ensure_mini_utopia_base()
    profile = _profile()
    world = assets.create_world(
        name="Fingerprint Garden",
        description=profile.source_description,
        profile=profile,
    )
    service = WorldConceptService(
        repo,
        storage,
        WorldConceptPromptService(),
        WorldBlueprintService(),
        FakeWorldImageProvider(),
    )
    scene_plan = WorldScenePlanService().plan_from_profile(profile=profile)
    service.plan_blueprint(
        location_asset_id=world.asset_id,
        style_asset_id=style.asset_id,
        scene_plan=scene_plan,
    )

    stale_profile = repo.get_asset(world.asset_id)
    assert stale_profile is not None
    stale_profile.metadata["world_profile"]["mood"] = ["Mysterious / 神秘"]
    repo.save_asset(stale_profile)
    with pytest.raises(ValueError, match="current Scene Plan and Profile"):
        service.render_blueprint_preview(
            location_asset_id=world.asset_id,
            style_asset_id=style.asset_id,
        )

    # Restore by rebuilding, then prove Scene Plan drift is guarded too.
    assets.update_world(
        asset_id=world.asset_id,
        name=profile.world_name,
        description=profile.source_description,
        profile=profile,
    )
    service.plan_blueprint(
        location_asset_id=world.asset_id,
        style_asset_id=style.asset_id,
        scene_plan=scene_plan,
    )
    stale_scene = repo.get_asset(world.asset_id)
    assert stale_scene is not None
    stale_scene.metadata["world_scene_plan"]["summary"] = "Changed without rebuild"
    repo.save_asset(stale_scene)
    with pytest.raises(ValueError, match="current Scene Plan and Profile"):
        service.render_blueprint_preview(
            location_asset_id=world.asset_id,
            style_asset_id=style.asset_id,
        )


def test_new_world_starts_unpublished_until_finish(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    assets = AssetService(repo)
    world = assets.create_world(
        name="Draft Garden",
        description="unfinished world",
        profile=_profile(),
    )

    saved = repo.get_asset(world.asset_id)
    assert saved is not None
    assert saved.metadata["world_creation_complete"] is False
    assert assets.is_world_library_visible(saved) is False

    completed = assets.complete_world(world.asset_id)
    assert completed.metadata["world_creation_complete"] is True
    assert assets.is_world_library_visible(completed) is True


def test_legacy_world_without_completion_metadata_remains_visible(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    world = AssetService(repo).create_world(
        name="Legacy Garden",
        description="legacy world",
        profile=_profile(),
    )
    world.metadata.pop("world_creation_complete", None)
    repo.save_asset(world)

    saved = repo.get_asset(world.asset_id)
    assert saved is not None
    assert AssetService.is_world_library_visible(saved) is True


def test_archive_world_hides_library_card_but_preserves_record(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    assets = AssetService(repo)
    world = assets.create_world(
        name="Finished Garden",
        description="finished world",
        profile=_profile(),
    )
    assets.complete_world(world.asset_id)

    archived = assets.archive_world(world.asset_id)

    assert archived.status == ReviewStatus.ARCHIVED
    assert assets.is_world_library_visible(archived) is False
    saved = repo.get_asset(world.asset_id)
    assert saved is not None
    assert saved.status == ReviewStatus.ARCHIVED
    assert saved.metadata["world_profile"]["world_name"] == "Candy Cloud Valley"
