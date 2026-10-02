from studio.core.enums import AssetType, ReviewStatus
from studio.models.world import WorldProfile
from studio.providers.base import ImageGenerationProvider
from studio.repositories.sqlite import SQLiteStudioRepository
from studio.services.asset_service import AssetService
from studio.services.style_service import StyleService
from studio.services.world_concept_prompt_service import WorldConceptPromptService
from studio.services.world_concept_service import WorldConceptService
from studio.services.world_blueprint_service import WorldBlueprintService
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
