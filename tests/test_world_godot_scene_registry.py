from pathlib import Path

from studio.core.enums import AssetType, ReviewStatus
from studio.models.asset import Asset
from studio.models.character import CharacterProfile
from studio.models.world import WorldProfile
from studio.repositories.sqlite import SQLiteStudioRepository
from studio.services.asset_service import AssetService
from studio.services.character_runtime_service import CharacterRuntimeService
from studio.services.play_session_service import CreatorPlaySessionService
from studio.services.world_runtime_binding_service import (
    NEWBIE_WORLD_ASSET_ID,
    NEWBIE_WORLD_SCENE_PATH,
    WorldRuntimeBindingService,
)
from studio.storage.local import LocalObjectStorage


ROOT = Path(__file__).resolve().parents[1]


def _user_world(
    repo: SQLiteStudioRepository,
    *,
    name: str,
    slug: str,
) -> Asset:
    asset = Asset.create(
        AssetType.LOCATION,
        display_name=name,
        slug=slug,
        status=ReviewStatus.APPROVED,
        metadata={
            "world_profile": WorldProfile(
                world_name=name,
                playable=True,
            ).model_dump(mode="json"),
            "world_creation_complete": True,
            "custom_marker": "KEEP_ME",
        },
    )
    repo.save_asset(asset)
    return asset


def _character(repo: SQLiteStudioRepository) -> Asset:
    asset = Asset.create(
        AssetType.CHARACTER,
        display_name="Nancy",
        slug="nancy",
        status=ReviewStatus.APPROVED,
        metadata={
            "character_profile": CharacterProfile().model_dump(mode="json"),
        },
    )
    repo.save_asset(asset)
    return asset


def test_builtin_newbie_world_registration_is_idempotent_and_non_destructive(tmp_path):
    db_path = tmp_path / "studio.db"
    repo = SQLiteStudioRepository(db_path)
    user_world = _user_world(
        repo,
        name="云鲸童话交通站",
        slug="cloud-whale-station",
    )
    before = repo.get_asset(user_world.asset_id).model_dump(mode="json")

    service = WorldRuntimeBindingService(repo)
    first = service.ensure_builtin_worlds()
    second = service.ensure_builtin_worlds()

    assert len(first) == 1
    assert len(second) == 1
    newbie = repo.get_asset(NEWBIE_WORLD_ASSET_ID)
    assert newbie is not None
    assert newbie.display_name == "新手村 / Newbie Village"
    assert AssetService.is_world_library_visible(newbie) is True
    assert newbie.metadata["world_blueprint"]["grid"]["width"] == 100
    assert newbie.metadata["world_blueprint"]["grid"]["depth"] == 100

    binding = service.binding_for(newbie.asset_id)
    assert binding is not None
    assert binding.scene_path == NEWBIE_WORLD_SCENE_PATH
    assert binding.source == "system_builtin"

    worlds = repo.list_assets(AssetType.LOCATION)
    assert sum(
        1
        for world in worlds
        if world.asset_id == NEWBIE_WORLD_ASSET_ID
    ) == 1

    after = repo.get_asset(user_world.asset_id).model_dump(mode="json")
    assert after == before


def test_existing_bound_world_prevents_duplicate_builtin_registration(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    existing = _user_world(
        repo,
        name="My Existing Newbie",
        slug="my-existing-newbie",
    )
    service = WorldRuntimeBindingService(repo)
    service.bind_scene(
        world_asset_id=existing.asset_id,
        scene_path=NEWBIE_WORLD_SCENE_PATH,
        scene_label="Already Bound",
        source="migration",
    )

    result = service.ensure_builtin_worlds()

    assert [world.asset_id for world in result] == [existing.asset_id]
    assert repo.get_asset(NEWBIE_WORLD_ASSET_ID) is None


def test_duplicate_world_names_are_disambiguated_without_deleting_assets(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    one = _user_world(repo, name="云鲸童话交通站", slug="station-one")
    two = _user_world(repo, name="云鲸童话交通站", slug="station-two")
    service = WorldRuntimeBindingService(repo)

    worlds = repo.list_assets(AssetType.LOCATION)
    labels = service.choice_labels(worlds)

    assert labels[one.asset_id] != labels[two.asset_id]
    assert one.asset_id[-6:] in labels[one.asset_id]
    assert two.asset_id[-6:] in labels[two.asset_id]
    assert len(repo.list_assets(AssetType.LOCATION)) == 2


def test_play_session_carries_same_world_asset_and_godot_scene_binding(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    service = WorldRuntimeBindingService(repo)
    service.ensure_builtin_worlds()
    character = _character(repo)

    session = CreatorPlaySessionService(
        repo,
        CharacterRuntimeService(
            repo,
            LocalObjectStorage(tmp_path / "storage"),
        ),
    ).build(
        character_asset_id=character.asset_id,
        world_asset_id=NEWBIE_WORLD_ASSET_ID,
    )

    assert session.world_asset_id == NEWBIE_WORLD_ASSET_ID
    assert session.world_name == "新手村 / Newbie Village"
    assert session.world_runtime is not None
    assert session.world_runtime.world_asset_id == NEWBIE_WORLD_ASSET_ID
    assert session.world_runtime.scene_path == NEWBIE_WORLD_SCENE_PATH


def test_creator_world_selectors_use_runtime_registry_labels():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    builder = (
        ROOT / "studio" / "ui" / "creator" / "story_builder.py"
    ).read_text(encoding="utf-8")

    assert "ctx.world_runtime_bindings.ensure_builtin_worlds()" in app
    assert "playable_world_labels = ctx.world_runtime_bindings.choice_labels(" in app
    assert "world_labels = ctx.world_runtime_bindings.choice_labels(worlds)" in builder
    assert "world_labels.get(asset.asset_id, asset.display_name)" in builder


def test_builtin_scene_path_exists_in_godot_project():
    relative = NEWBIE_WORLD_SCENE_PATH.removeprefix("res://")
    assert (ROOT / "godot" / relative).exists()
