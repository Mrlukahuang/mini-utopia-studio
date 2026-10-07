from pathlib import Path

import pytest

from studio.core.enums import AssetType, StoryMode
from studio.models.asset import Asset
from studio.models.character import CharacterProfile
from studio.models.equipment import EquipmentSlot
from studio.repositories.sqlite import SQLiteStudioRepository
from studio.services.baby_service import BabyService
from studio.services.character_runtime_service import CharacterRuntimeService
from studio.services.director_shot_session_service import (
    DirectorShotSessionService,
)
from studio.services.episode_service import EpisodeService
from studio.services.equipment_service import EquipmentService
from studio.services.scene_breakdown_service import SceneBreakdownService
from studio.services.shot_plan_service import ShotPlanService
from studio.services.story_service import StoryService
from studio.storage.local import LocalObjectStorage


ROOT = Path(__file__).resolve().parents[1]


def _production_state(repo: SQLiteStudioRepository):
    character = Asset.create(
        AssetType.CHARACTER,
        display_name="Nancy",
        slug="nancy",
        metadata={
            "character_profile": CharacterProfile().model_dump(mode="json"),
        },
    )
    world = Asset.create(
        AssetType.LOCATION,
        display_name="Newbie Village",
        slug="newbie-village",
    )
    repo.save_asset(character)
    repo.save_asset(world)

    babies = BabyService(repo)
    babies.create_initial_baby(
        display_name="Nova",
        species_id="star_baby",
    )

    equipment = EquipmentService(repo)
    collection = equipment.ensure_starter_collection()
    definitions = equipment.list_definitions()
    sword = next(
        item
        for item in collection.items
        if definitions[item.definition_id].slot
        == EquipmentSlot.WEAPON_MAIN
    )
    equipment.equip(
        character_asset_id=character.asset_id,
        item_instance_id=sword.item_instance_id,
    )

    story = StoryService(repo).create_story(
        title="Director Portal Adventure",
        premise="Nancy and Nova walk toward the Portal.",
        mode=StoryMode.PLAYGROUND,
        asset_ids=[character.asset_id, world.asset_id],
        hook="Nancy and Nova enter Newbie Village.",
        ending="They stop in front of the glowing Portal.",
    )
    episode = EpisodeService(repo).create_from_story(story.story_id)
    episode = SceneBreakdownService(repo).build_from_story(
        episode.episode_id
    )
    episode = ShotPlanService(repo).build_for_episode(
        episode.episode_id
    )
    return character, world, babies, equipment, episode


def _director_service(
    repo: SQLiteStudioRepository,
    storage_root: Path,
    export_path: Path,
) -> DirectorShotSessionService:
    return DirectorShotSessionService(
        repo,
        CharacterRuntimeService(
            repo,
            LocalObjectStorage(storage_root),
        ),
        equipment=EquipmentService(repo),
        babies=BabyService(repo),
        export_path=export_path,
    )


def test_director_shot_contains_same_world_character_equipment_baby_and_camera(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    character, world, _babies, _equipment, episode = _production_state(repo)
    shot = episode.scenes[0].shots[0]

    service = _director_service(
        repo,
        tmp_path / "storage",
        tmp_path / "director.json",
    )
    session = service.export(
        episode_id=episode.episode_id,
        scene_id=episode.scenes[0].scene_id,
        shot_id=shot.shot_id,
    )

    assert session.episode_id == episode.episode_id
    assert session.scene_id == episode.scenes[0].scene_id
    assert session.shot_id == shot.shot_id
    assert session.character_asset_id == character.asset_id
    assert session.world_asset_id == world.asset_id
    assert session.duration_seconds == shot.duration_seconds
    assert session.camera.position
    assert session.camera.look_at
    assert session.animation_intent in {"idle", "walk", "run", "attack"}

    play = session.play_session
    assert play.source == "director"
    assert play.character_asset_id == character.asset_id
    assert play.world_asset_id == world.asset_id
    assert play.baby is not None
    assert play.baby.display_name == "Nova"
    assert play.equipment.equipped["weapon_main"].display_name
    assert play.equipment.final_stats.atk > 10

    saved = (tmp_path / "director.json").read_text(encoding="utf-8")
    assert session.director_session_id in saved
    assert character.asset_id in saved
    assert world.asset_id in saved
    assert "Nova" in saved


def test_director_export_is_deterministic_across_restart_for_unchanged_state(tmp_path):
    db_path = tmp_path / "studio.db"
    repo = SQLiteStudioRepository(db_path)
    _character, _world, _babies, _equipment, episode = _production_state(repo)
    scene = episode.scenes[-1]
    shot = scene.shots[0]

    first = _director_service(
        repo,
        tmp_path / "storage",
        tmp_path / "first.json",
    ).build(
        episode_id=episode.episode_id,
        scene_id=scene.scene_id,
        shot_id=shot.shot_id,
    )

    restarted_repo = SQLiteStudioRepository(db_path)
    second = _director_service(
        restarted_repo,
        tmp_path / "storage",
        tmp_path / "second.json",
    ).build(
        episode_id=episode.episode_id,
        scene_id=scene.scene_id,
        shot_id=shot.shot_id,
    )

    assert second.director_session_id == first.director_session_id
    assert second.source_fingerprint == first.source_fingerprint
    assert second.model_dump_json() == first.model_dump_json()


def test_director_shot_rejects_invalid_episode_scene_and_shot_ids(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    _character, _world, _babies, _equipment, episode = _production_state(repo)
    service = _director_service(
        repo,
        tmp_path / "storage",
        tmp_path / "director.json",
    )

    with pytest.raises(ValueError, match="Episode not found"):
        service.build(
            episode_id="EP_MISSING",
            scene_id="SCENE_01",
            shot_id="SHOT_01_01",
        )

    with pytest.raises(ValueError, match="Scene not found"):
        service.build(
            episode_id=episode.episode_id,
            scene_id="SCENE_MISSING",
            shot_id="SHOT_01_01",
        )

    with pytest.raises(ValueError, match="Shot not found"):
        service.build(
            episode_id=episode.episode_id,
            scene_id=episode.scenes[0].scene_id,
            shot_id="SHOT_MISSING",
        )


def test_episode_ui_and_godot_runtime_expose_director_mode():
    ui = (
        ROOT / "studio" / "ui" / "creator" / "episodes.py"
    ).read_text(encoding="utf-8")
    runtime = (
        ROOT / "godot" / "scripts" / "director_shot_runtime.gd"
    ).read_text(encoding="utf-8")
    creator_runtime = (
        ROOT / "godot" / "scripts" / "creator_play_runtime.gd"
    ).read_text(encoding="utf-8")

    assert "Stage Shot / 导演模式" in ui
    assert "DirectorShotSessionService" in ui
    assert "Godot Director payload ready" in ui
    assert "class_name MiniUtopiaDirectorShotRuntime" in runtime
    assert "DirectorCamera" in runtime
    assert "DirectorActor" in runtime
    assert "advance_shot" in runtime
    assert "apply_payload_to_player" in creator_runtime
